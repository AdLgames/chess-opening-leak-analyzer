#!/usr/bin/env python3
"""Opening Leak Lab as a single Vercel Python function.

Differences from the local server (`chess-dashboard/api_server.py`):

* One synchronous endpoint. A serverless invocation cannot outlive its response,
  and consecutive requests may land on different instances, so there is no job
  registry to poll — `/api/analyze` runs the pipeline and returns the report.
* The Stockfish binary ships in the deployment but `/var/task` is read-only and
  loses the executable bit, so it is copied to `/tmp` and chmod'ed on cold start.
* Work is clamped to fit the function's time budget (see LIMITS).
"""
from __future__ import annotations

import csv
import io
import os
import shutil
import stat
import sys
import tempfile
import time
import traceback
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --------------------------------------------------------------- engine bootstrap
BUNDLED_ENGINE = os.path.join(ROOT, "engine", "stockfish")
RUNTIME_DIR = os.path.join(tempfile.gettempdir(), "leaklab-engine")
RUNTIME_ENGINE = os.path.join(RUNTIME_DIR, "stockfish")


def prepare_engine() -> str | None:
    """Copy the shipped binary into /tmp and make it executable. Returns its path."""
    if not os.path.isfile(BUNDLED_ENGINE):
        return None
    try:
        os.makedirs(RUNTIME_DIR, exist_ok=True)
        if not os.path.isfile(RUNTIME_ENGINE) or \
                os.path.getsize(RUNTIME_ENGINE) != os.path.getsize(BUNDLED_ENGINE):
            tmp = RUNTIME_ENGINE + ".part"
            shutil.copyfile(BUNDLED_ENGINE, tmp)
            os.chmod(tmp, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
            os.replace(tmp, RUNTIME_ENGINE)
        os.environ["STOCKFISH_PATH"] = RUNTIME_ENGINE
        return RUNTIME_ENGINE
    except OSError:
        traceback.print_exc()
        return None


ENGINE_PATH = prepare_engine()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402

from chessopening.analyze import analyze  # noqa: E402
from chessopening.engine import find_engine  # noqa: E402
from chessopening.localdb import DEFAULT_DB, LocalOpeningDatabase  # noqa: E402
from chessopening.pgn_loader import detect_main_player, find_pgn_files  # noqa: E402
from chessopening.summary import summarise  # noqa: E402

SAMPLE_DIR = os.path.join(ROOT, "sample_pgns")
WORK_ROOT = os.path.join(tempfile.gettempdir(), "leaklab")
os.makedirs(WORK_ROOT, exist_ok=True)

# what one invocation is allowed to attempt — the function has 60s and 3 GB
LIMITS = {
    "max_upload_mb": 8,
    "max_games": 120,
    "max_depth": 14,
    "max_multipv": 3,
    "max_moves": 15,
    "time_budget_s": 42.0,
}

app = FastAPI(title="Opening Leak Lab API (serverless)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ------------------------------------------------------------------------- meta
def engine_info() -> dict[str, Any]:
    try:
        path = find_engine()
    except FileNotFoundError as exc:
        return {"available": False, "detail": str(exc)}
    import subprocess  # noqa: PLC0415

    try:
        out = subprocess.run([path], input="uci\nquit\n", capture_output=True, text=True,
                             timeout=20).stdout
        name = next((l.split("id name ", 1)[1] for l in out.splitlines()
                     if l.startswith("id name")), "Stockfish")
    except Exception:  # noqa: BLE001
        return {"available": False, "detail": f"{path} did not answer UCI on this host"}
    return {"available": True, "name": name, "path": "bundled in the function", "bundled": True}


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
    files = find_pgn_files(SAMPLE_DIR) if os.path.isdir(SAMPLE_DIR) else []
    player = detect_main_player(files) if files else None
    return {
        "engine": engine_info(),
        "database": db_info(),
        "sample": {"available": bool(files), "files": len(files), "player": player},
        "defaults": {"depth": 12, "max_moves": 15, "min_games": 3, "eval_drop": 0.8,
                     "score_gap": 6.0, "min_db_games": 20, "multipv": 3},
        "serverless": True,
        "limits": LIMITS,
    }


# -------------------------------------------------------------------------- run
def _clamp(name: str, value: float, hi: float) -> tuple[float, str | None]:
    if value > hi:
        return hi, f"{name} clamped to {hi:g} on the hosted deployment"
    return value, None


@app.post("/api/analyze")
async def analyse(
    files: list[UploadFile] = File(default=[]),
    use_sample: str = Form("false"),
    player: str = Form(""),
    color: str = Form("both"),
    depth: int = Form(12),
    multipv: int = Form(3),
    max_moves: int = Form(15),
    min_games: int = Form(3),
    eval_drop: float = Form(0.8),
    score_gap: float = Form(6.0),
    min_db_games: int = Form(20),
    no_engine: str = Form("false"),
) -> JSONResponse:
    started = time.time()
    log: list[str] = []
    notes: list[str] = []
    sample = use_sample.lower() == "true"
    work = tempfile.mkdtemp(prefix="run-", dir=WORK_ROOT)

    try:
        if sample:
            pgn_dir = SAMPLE_DIR
            if not find_pgn_files(pgn_dir):
                raise HTTPException(400, "Sample archive is not installed")
        else:
            real = [f for f in files if f.filename]
            if not real:
                raise HTTPException(400, "Upload at least one PGN file")
            pgn_dir = os.path.join(work, "pgn")
            os.makedirs(pgn_dir, exist_ok=True)
            budget = LIMITS["max_upload_mb"] * 1024 * 1024
            total = 0
            for f in real:
                if not f.filename.lower().endswith(".pgn"):
                    raise HTTPException(400, f"{f.filename}: only .pgn files are accepted")
                data = await f.read()
                total += len(data)
                if total > budget:
                    raise HTTPException(
                        413,
                        f"The hosted deployment accepts {LIMITS['max_upload_mb']} MB per run. "
                        "Run the analyzer locally for a full archive.")
                with open(os.path.join(pgn_dir, os.path.basename(f.filename)), "wb") as out:
                    out.write(data)

        for label, val, hi in (("depth", depth, LIMITS["max_depth"]),
                              ("multipv", multipv, LIMITS["max_multipv"]),
                              ("opening length", max_moves, LIMITS["max_moves"])):
            new, note = _clamp(label, val, hi)
            if note:
                notes.append(note)
            if label == "depth":
                depth = int(new)
            elif label == "multipv":
                multipv = int(new)
            else:
                max_moves = int(new)

        if not player:
            player = detect_main_player(find_pgn_files(pgn_dir)) or ""
            if not player:
                raise HTTPException(400, "No player name found in the PGN headers")
            log.append(f"Auto-detected player: {player}")

        out_dir = os.path.join(work, "out")
        os.makedirs(out_dir, exist_ok=True)
        result = analyze(
            pgn_dir=pgn_dir,
            player=player,
            out_dir=out_dir,
            depth=int(depth),
            multipv=int(multipv),
            threads=2,
            max_moves=int(max_moves),
            color=color,
            min_games=int(min_games),
            eval_drop_threshold=float(eval_drop),
            score_gap_threshold=float(score_gap) / 100.0,
            db="local",
            min_db_games=int(min_db_games),
            no_engine=no_engine.lower() == "true",
            max_games=int(LIMITS["max_games"]),
            engine_budget_s=float(LIMITS["time_budget_s"]),
            cache_dir=os.path.join(WORK_ROOT, "_cache"),
            log=lambda *parts: log.append(" ".join(str(p) for p in parts)),
        )
        with open(result["report"], encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))

        payload = {
            "player": player,
            "summary": summarise(rows, result),
            "rows": rows,
            "log": log[-40:],
            "notes": notes + list(result.get("notes", [])),
            "elapsed": round(time.time() - started, 1),
            "options": {"depth": depth, "color": color, "max_moves": max_moves,
                        "min_games": min_games, "eval_drop": eval_drop, "score_gap": score_gap,
                        "min_db_games": min_db_games, "multipv": multipv,
                        "no_engine": no_engine.lower() == "true"},
            "csv": _csv_text(rows),
        }
        return JSONResponse(payload)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _csv_text(rows: list[dict[str, str]]) -> str:
    """The report as CSV text, so the browser can offer a download without a job id."""
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


@app.get("/api/sample-archive")
def sample_archive() -> Response:
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
    return {"ok": True, "engine": bool(ENGINE_PATH), "serverless": True}


# On Vercel the CDN serves `public/`, so this mount never sees traffic there. Locally it
# makes `uvicorn api.index:app` a complete preview of the hosted build on one port.
_PUBLIC = os.path.join(ROOT, "public")
if os.path.isdir(_PUBLIC):
    from fastapi.staticfiles import StaticFiles  # noqa: PLC0415

    app.mount("/", StaticFiles(directory=_PUBLIC, html=True), name="public")
