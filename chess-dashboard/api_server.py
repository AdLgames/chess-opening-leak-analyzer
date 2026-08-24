#!/usr/bin/env python3
"""Backend for the Opening Leak Lab dashboard.

Wraps the chessopening analyzer: uploads PGNs, runs Stockfish + the local opening
database in a worker thread, and serves the report as JSON/CSV. Port 8000.
"""
from __future__ import annotations

import csv
import io
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import uuid
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
# the analyzer package may sit beside the server or in a sibling project folder
# prefer a copy sitting next to this file; fall back to the sibling analyzer project
for _cand in (_HERE, os.path.join(os.path.dirname(_HERE), "chess_opening_analyzer")):
    if os.path.isdir(os.path.join(_cand, "chessopening")) and _cand not in sys.path:
        sys.path.append(_cand)

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from chessopening.analyze import analyze
from chessopening.engine import find_engine
from chessopening.localdb import DEFAULT_DB, LocalOpeningDatabase
from chessopening.pgn_loader import detect_main_player, find_pgn_files
from chessopening.summary import summarise

ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(ROOT, "sample_pgns")
JOBS_ROOT = os.path.join(tempfile.gettempdir(), "leaklab-jobs")
os.makedirs(JOBS_ROOT, exist_ok=True)

app = FastAPI(title="Opening Leak Lab API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

JOBS: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()
MAX_UPLOAD_BYTES = 40 * 1024 * 1024


# --------------------------------------------------------------------------- meta
def engine_info() -> dict[str, Any]:
    try:
        path = find_engine()
    except FileNotFoundError as exc:
        return {"available": False, "detail": str(exc)}
    import subprocess

    try:
        out = subprocess.run([path], input="uci\nquit\n", capture_output=True, text=True,
                             timeout=20).stdout
        name = next((l.split("id name ", 1)[1] for l in out.splitlines() if l.startswith("id name")), "Stockfish")
    except Exception:  # noqa: BLE001
        name = "Stockfish"
    return {"available": True, "name": name, "path": os.path.relpath(path, ROOT), "bundled": ROOT in path}


def db_info() -> dict[str, Any]:
    if not os.path.exists(DEFAULT_DB):
        return {"available": False}
    db = LocalOpeningDatabase(DEFAULT_DB)
    meta = dict(db._meta)  # noqa: SLF001 - simple read of the meta table
    positions = db.con.execute("SELECT COUNT(DISTINCT pos) FROM moves").fetchone()[0]
    rows = db.con.execute("SELECT COUNT(*) FROM moves").fetchone()[0]
    named = db.con.execute("SELECT COUNT(*) FROM openings").fetchone()[0]
    db.close()
    return {
        "available": True,
        "games": int(meta.get("games", 0) or 0),
        "positions": positions,
        "move_rows": rows,
        "named_openings": named,
        "filters": meta.get("filters", ""),
        "source": meta.get("source", ""),
        "built_at": meta.get("built_at", ""),
        "size_mb": round(os.path.getsize(DEFAULT_DB) / 1e6, 1),
    }


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    players: list[str] = []
    files = find_pgn_files(SAMPLE_DIR) if os.path.isdir(SAMPLE_DIR) else []
    if files:
        guess = detect_main_player(files)
        if guess:
            players = [guess]
    return {
        "engine": engine_info(),
        "database": db_info(),
        "sample": {"available": bool(files), "files": len(files), "player": players[0] if players else None},
        "defaults": {"depth": 16, "max_moves": 15, "min_games": 3, "eval_drop": 0.8,
                     "score_gap": 6.0, "min_db_games": 20, "multipv": 3},
    }


# --------------------------------------------------------------------------- run
_summarise = summarise  # shared with the serverless deployment


def _run_job(job_id: str, pgn_dir: str, player: str | None, opts: dict[str, Any]) -> None:
    job = JOBS[job_id]
    out_dir = os.path.join(JOBS_ROOT, job_id)
    os.makedirs(out_dir, exist_ok=True)

    def log(*parts: Any) -> None:
        line = " ".join(str(p) for p in parts)
        with LOCK:
            job["log"].append(line)
            job["log"][:] = job["log"][-80:]
            job["updated"] = time.time()

    try:
        job["status"] = "running"
        if not player:
            player = detect_main_player(find_pgn_files(pgn_dir))
            if not player:
                raise ValueError("No player name found in the PGN headers")
            log(f"Auto-detected player: {player}")
        job["player"] = player
        result = analyze(
            pgn_dir=pgn_dir,
            player=player,
            out_dir=out_dir,
            depth=int(opts["depth"]),
            multipv=int(opts["multipv"]),
            threads=2,
            max_moves=int(opts["max_moves"]),
            color=opts["color"],
            min_games=int(opts["min_games"]),
            eval_drop_threshold=float(opts["eval_drop"]),
            score_gap_threshold=float(opts["score_gap"]) / 100.0,
            db="local",
            min_db_games=int(opts["min_db_games"]),
            no_engine=bool(opts["no_engine"]),
            cache_dir=os.path.join(JOBS_ROOT, "_cache"),
            log=log,
        )
        with open(result["report"], encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        with LOCK:
            job["rows"] = rows
            job["summary"] = _summarise(rows, result)
            job["report_path"] = result["report"]
            job["status"] = "done"
            job["finished"] = time.time()
        log(f"Report ready: {len(rows)} flagged decisions")
    except Exception as exc:  # noqa: BLE001
        with LOCK:
            job["status"] = "error"
            job["error"] = f"{type(exc).__name__}: {exc}"
            job["log"].append(job["error"])
        traceback.print_exc()
    finally:
        if job.get("temp_dir"):
            shutil.rmtree(job["temp_dir"], ignore_errors=True)


@app.post("/api/analyze")
async def start_analysis(
    background: BackgroundTasks,
    files: list[UploadFile] = File(default=[]),
    use_sample: str = Form("false"),
    player: str = Form(""),
    color: str = Form("both"),
    depth: int = Form(16),
    multipv: int = Form(3),
    max_moves: int = Form(15),
    min_games: int = Form(3),
    eval_drop: float = Form(0.8),
    score_gap: float = Form(6.0),
    min_db_games: int = Form(20),
    no_engine: str = Form("false"),
    x_visitor_id: str = Header(default="anon"),
) -> dict[str, Any]:
    sample = use_sample.lower() == "true"
    temp_dir = None
    if sample:
        pgn_dir = SAMPLE_DIR
        if not os.path.isdir(pgn_dir):
            raise HTTPException(400, "Sample archive is not installed")
    else:
        real = [f for f in files if f.filename]
        if not real:
            raise HTTPException(400, "Upload at least one PGN file")
        temp_dir = tempfile.mkdtemp(prefix="leaklab-upload-")
        total = 0
        for f in real:
            if not f.filename.lower().endswith(".pgn"):
                raise HTTPException(400, f"{f.filename}: only .pgn files are accepted")
            data = await f.read()
            total += len(data)
            if total > MAX_UPLOAD_BYTES:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise HTTPException(413, "Upload limit is 40 MB per run")
            with open(os.path.join(temp_dir, os.path.basename(f.filename)), "wb") as out:
                out.write(data)
        pgn_dir = temp_dir

    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "id": job_id, "status": "queued", "log": [], "rows": [], "summary": None,
        "visitor": x_visitor_id, "created": time.time(), "updated": time.time(),
        "temp_dir": temp_dir, "player": player or None, "source": "sample" if sample else "upload",
        "options": {"depth": depth, "color": color, "max_moves": max_moves, "min_games": min_games,
                    "eval_drop": eval_drop, "score_gap": score_gap, "min_db_games": min_db_games,
                    "multipv": multipv, "no_engine": no_engine.lower() == "true"},
    }
    opts = dict(JOBS[job_id]["options"])
    background.add_task(_run_job, job_id, pgn_dir, player or None, opts)
    return {"job_id": job_id, "status": "queued"}


def _job_or_404(job_id: str) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job")
    return job


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)
    return {
        "id": job_id,
        "status": job["status"],
        "player": job.get("player"),
        "source": job.get("source"),
        "options": job.get("options"),
        "log": job["log"][-14:],
        "error": job.get("error"),
        "elapsed": round((job.get("finished") or time.time()) - job["created"], 1),
        "leaks": len(job["rows"]),
    }


@app.get("/api/report/{job_id}")
def report(job_id: str) -> JSONResponse:
    job = _job_or_404(job_id)
    if job["status"] != "done":
        raise HTTPException(409, f"Job is {job['status']}")
    return JSONResponse({"summary": job["summary"], "rows": job["rows"], "player": job.get("player")})


@app.get("/api/report/{job_id}/csv")
def report_csv(job_id: str) -> Response:
    job = _job_or_404(job_id)
    path = job.get("report_path")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "No CSV for this job")
    return FileResponse(path, media_type="text/csv", filename=f"opening_leaks_{job_id}.csv")


@app.get("/api/sample-archive")
def sample_archive() -> Response:
    """Download the demo PGN archive so users can see the expected input format."""
    files = find_pgn_files(SAMPLE_DIR)
    if not files:
        raise HTTPException(404, "No sample archive")
    buf = io.StringIO()
    for p in files:
        with open(p, encoding="utf-8") as fh:
            buf.write(fh.read())
            buf.write("\n")
    return Response(buf.getvalue(), media_type="application/x-chess-pgn",
                    headers={"Content-Disposition": 'attachment; filename="sample_games.pgn"'})


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "jobs": len(JOBS)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
