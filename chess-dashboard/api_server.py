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
import sqlite3
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

from fastapi import (BackgroundTasks, FastAPI, File, Form, Header, HTTPException, Request,
                     UploadFile)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from chessopening.analyze import analyze
from chessopening.board import BoardError, cp_text, engine_lines, position_payload
from chessopening.engine import find_engine
from chessopening.ingest import (DEFAULT_CACHE, FetchOptions, IngestError, fetch_games,
                                 lookup_player, provider_label, speeds_from_csv)
from chessopening.guard import RateLimiter, allowed_origins, client_key
from chessopening.localdb import DEFAULT_DB, LocalOpeningDatabase
from chessopening.marks import DEFAULT_STATE, GapStore, MarkStore
from chessopening.messages import explain_failure
from chessopening.history import HistoryStore
from chessopening.review import ReviewStore, describe_due, grade_for_loss
from chessopening.pgn_loader import detect_main_player, find_pgn_files
from chessopening.summary import summarise

ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(ROOT, "sample_pgns")
JOBS_ROOT = os.path.join(tempfile.gettempdir(), "leaklab-jobs")
os.makedirs(JOBS_ROOT, exist_ok=True)

app = FastAPI(title="Opening Leak Lab API")
# Localhost only, unless the operator names somewhere else. The previous "*" meant any
# page the user had open in another tab could read their game history off this port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Lichess-Token"],
)

# Analysis is the expensive one — each job spawns an engine and reads an archive — so it
# gets a much tighter budget than the read endpoints the dashboard polls constantly.
ANALYZE_LIMIT = RateLimiter(int(os.environ.get("LEAKLAB_ANALYZE_PER_HOUR", "20")), 3600)
READ_LIMIT = RateLimiter(int(os.environ.get("LEAKLAB_READS_PER_MINUTE", "600")), 60)


# Paths that cost real work: an analysis spawns an engine and reads an archive, and an
# engine probe is a search. Everything else is a SQLite read the dashboard polls freely.
COSTLY = ("/api/analyze", "/api/engine")


@app.middleware("http")
async def throttle(request: Request, call_next):
    """Bound accidents — a runaway script, a page stuck in a retry loop.

    Not a defence against a determined attacker: this is one process with an in-memory
    counter. It stops a mistake from queueing a hundred engine jobs, which is the failure
    that actually happens.
    """
    if request.method == "OPTIONS" or not request.url.path.startswith("/api/"):
        return await call_next(request)
    costly = any(request.url.path.startswith(p) for p in COSTLY)
    limiter = ANALYZE_LIMIT if costly else READ_LIMIT
    key = client_key(request.client.host if request.client else None,
                     request.headers.get("x-forwarded-for"))
    allowed, retry_after = limiter.check(key)
    if not allowed:
        what = "analysis runs" if costly else "requests"
        return JSONResponse(
            status_code=429,
            content={"detail": f"That is a lot of {what} at once. "
                               f"Try again in {retry_after} seconds."},
            headers={"Retry-After": str(retry_after)},
        )
    return await call_next(request)

JOBS: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
ENGINE_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "leaklab", "board_evals.json")

# one shared read-only handle for the board panes; SQLite reads are thread safe here
_BOARD_DB: LocalOpeningDatabase | None = None
_BOARD_DB_LOCK = threading.Lock()


def board_db() -> LocalOpeningDatabase | None:
    global _BOARD_DB  # noqa: PLW0603 - deliberate module-level singleton
    if _BOARD_DB is None and os.path.exists(DEFAULT_DB):
        with _BOARD_DB_LOCK:
            if _BOARD_DB is None:
                try:
                    _BOARD_DB = LocalOpeningDatabase(DEFAULT_DB)
                except sqlite3.DatabaseError:
                    # An unpulled Git LFS pointer. The board still draws and the engine
                    # still runs; only the book panel has nothing to say, which the page
                    # already handles. A 500 here would take the whole board down.
                    return None
                _BOARD_DB.con.close()
                _BOARD_DB.con = sqlite3.connect(DEFAULT_DB, check_same_thread=False)
                _BOARD_DB.con.row_factory = sqlite3.Row
    return _BOARD_DB


# --------------------------------------------------------------------------- meta
def engine_info() -> dict[str, Any]:
    try:
        path = find_engine()
    except FileNotFoundError as exc:
        # The raw text is the right thing on a terminal and the wrong thing in a browser,
        # so both travel: `detail` for anyone reading a log, `explain` for the page.
        return {"available": False, "detail": str(exc), "explain": explain_failure(exc)}
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
        return {"available": False,
                "explain": explain_failure(f"Local opening database not found at {DEFAULT_DB}")}
    try:
        db = LocalOpeningDatabase(DEFAULT_DB)
    except sqlite3.DatabaseError as exc:
        # The book ships through Git LFS, so before `git lfs pull` this path holds a small
        # text pointer that opens fine and then fails as a database. Letting that become a
        # 500 takes the whole page down over a file that simply has not downloaded yet.
        return {"available": False, "explain": explain_failure(exc)}
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
        "ingest": {"providers": ["chesscom", "lichess"], "default_provider": "chesscom",
                   "max_games": 400, "speeds": ["bullet", "blitz", "rapid", "classical", "daily"]},
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
        fetch = job.get("fetch")
        if fetch:
            log(f"Fetching games for {fetch['username']} from {provider_label(fetch['provider'])}")
            try:
                fetched = fetch_games(FetchOptions(**fetch), progress=log)
            except IngestError as exc:
                with LOCK:
                    job["status"] = "error"
                    job["error"] = str(exc)
                    job["hint"] = exc.hint
                    job["download_url"] = exc.download_url
                    job["log"].append(str(exc))
                    if exc.hint:
                        job["log"].append(exc.hint)
                return
            pgn_dir = fetched.pgn_dir
            player = player or fetched.username
            with LOCK:
                job["fetched"] = fetched.to_dict()
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
            # Kept so the next run can answer "did last month's work do anything?".
            try:
                store = HistoryStore(DEFAULT_STATE)
                try:
                    store.save_run(job["summary"], rows, player=player or "",
                                   source=job.get("source", ""), options=opts)
                    job["comparison"] = store.compare_latest()
                finally:
                    store.close()
            except Exception as err:  # noqa: BLE001 - history is a nicety, never a blocker
                log(f"could not record this run in your history: {err}")
            job["report_path"] = result["report"]
            job["status"] = "done"
            job["finished"] = time.time()
        log(f"Report ready: {len(rows)} flagged decisions")
    except Exception as exc:  # noqa: BLE001
        with LOCK:
            job["status"] = "error"
            job["error"] = f"{type(exc).__name__}: {exc}"
            job["explain"] = explain_failure(exc)
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
    source: str = Form(""),
    username: str = Form(""),
    provider: str = Form("chesscom"),
    max_games: int = Form(200),
    time_classes: str = Form("blitz,rapid,classical"),
    include_unrated: str = Form("false"),
    since: str = Form(""),
    until: str = Form(""),
    lichess_token: str = Form(""),
    refresh: str = Form("false"),
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
    sample = use_sample.lower() == "true" or source == "sample"
    by_username = source == "username" or (bool(username.strip()) and not sample and not source)
    temp_dir = None
    fetch_spec: dict[str, Any] | None = None
    if by_username:
        try:
            fetch_spec = FetchOptions(
                provider=provider,
                username=username.strip(),
                max_games=max(1, min(int(max_games), 400)),
                speeds=speeds_from_csv(time_classes),
                rated_only=include_unrated.lower() != "true",
                since=since.strip() or None,
                until=until.strip() or None,
                token=lichess_token.strip() or None,
                cache_dir=os.path.join(DEFAULT_CACHE),
                refresh=refresh.lower() == "true",
            ).normalised().__dict__
        except IngestError as exc:
            raise HTTPException(400, str(exc)) from exc
        pgn_dir = ""
    elif sample:
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
        "temp_dir": temp_dir, "player": player or None,
        "source": "username" if by_username else ("sample" if sample else "upload"),
        "fetch": fetch_spec,
        "account": {"provider": fetch_spec["provider"], "username": fetch_spec["username"]} if fetch_spec else None,
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
        "explain": job.get("explain"),
        "hint": job.get("hint"),
        "download_url": job.get("download_url"),
        "account": job.get("account"),
        "fetched": job.get("fetched"),
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


@app.get("/api/lookup")
def lookup(provider: str = "chesscom", username: str = "") -> dict[str, Any]:
    """Confirm a username before a run, and show whose games are about to be read."""
    try:
        return {"found": True, "profile": lookup_player(provider, username)}
    except IngestError as exc:
        return {"found": False, "error": str(exc), "hint": exc.hint}


# ------------------------------------------------------------------- board panes
@app.get("/api/position")
def position(fen: str = "", moves: str = "", san: str = "", book: str = "true") -> dict[str, Any]:
    """Legal moves, naming and book statistics for one position.

    `moves` is a comma-separated UCI list applied from `fen` (or the initial position),
    which is how the explorer walks a line without trusting the browser for legality.
    """
    try:
        return position_payload(
            fen.strip() or None,
            [m for m in moves.split(",") if m.strip()],
            db=board_db() if book.lower() != "false" else None,
            san=[m for m in san.replace(",", " ").split() if m.strip()],
        )
    except BoardError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/engine")
def engine_eval(payload: dict[str, Any]) -> dict[str, Any]:
    """Stockfish's top continuations for a position the user is looking at."""
    fen = str(payload.get("fen") or "").strip()
    if not fen:
        raise HTTPException(400, "fen is required")
    try:
        result = engine_lines(
            fen,
            depth=int(payload.get("depth") or 14),
            multipv=int(payload.get("multipv") or 3),
            pv_len=int(payload.get("pv_len") or 6),
            cache_path=ENGINE_CACHE,
        )
    except FileNotFoundError as exc:
        # The friendly version travels with the failure, so every caller renders the same
        # sentence rather than each one inventing its own wording for the same problem.
        raise HTTPException(503, explain_failure(exc)) from exc
    except BoardError as exc:
        raise HTTPException(400, str(exc)) from exc
    for line in result.get("lines", []):
        line["eval"] = cp_text(line.get("cp"))
    return result


@app.get("/api/openings")
def openings(q: str = "", limit: int = 30) -> dict[str, Any]:
    """Named openings from the local book, for the library search box."""
    db = board_db()
    if db is None:
        raise HTTPException(503, explain_failure("Local opening database not found"))
    return {"query": q, "results": db.search_openings(q, max(1, min(int(limit), 100)))}


@app.get("/api/repertoire")
def repertoire_marks() -> dict[str, Any]:
    """Every decision the player has recorded about their own openings."""
    store = MarkStore(DEFAULT_STATE)
    try:
        return {"marks": store.listing()}
    finally:
        store.close()


@app.post("/api/repertoire")
def set_repertoire_mark(payload: dict[str, Any]) -> dict[str, Any]:
    """Commit to a move, ignore a finding, or undo either.

    `decision: "clear"` removes whatever was there, so the player can change their mind
    without a second endpoint.
    """
    epd = str(payload.get("epd") or "").strip()
    color = str(payload.get("color") or "").strip()
    decision = str(payload.get("decision") or "").strip()
    if not epd or color not in ("white", "black"):
        raise HTTPException(400, "epd and a colour of white or black are required")

    store = MarkStore(DEFAULT_STATE)
    try:
        if decision == "clear":
            return {"ok": True, "cleared": store.clear(epd, color)}
        try:
            mark = store.set(
                epd, color,
                str(payload.get("uci") or "").strip(),
                decision,
                san=str(payload.get("san") or "").strip(),
                note=str(payload.get("note") or "").strip(),
            )
        except ValueError as err:
            raise HTTPException(400, str(err)) from err
        return {"ok": True, "mark": mark.__dict__}
    finally:
        store.close()


@app.get("/api/gaps")
def gap_decisions() -> dict[str, Any]:
    """What the player has decided about the replies they are not ready for."""
    store = GapStore(DEFAULT_STATE)
    try:
        return {"decisions": store.listing()}
    finally:
        store.close()


@app.post("/api/gaps")
def decide_gap(payload: dict[str, Any]) -> dict[str, Any]:
    """Learn it, practise it, or stop being told about it.

    "Practising" also enrols the position in the review cycle, so choosing it in one place
    does the thing rather than only recording an intention. The move to grade against comes
    from the report, which looked it up in the book when the gap was found.
    """
    epd = str(payload.get("epd") or "").strip()
    color = str(payload.get("color") or "").strip()
    decision = str(payload.get("decision") or "").strip()
    if not epd or color not in ("white", "black"):
        raise HTTPException(400, "epd and a colour of white or black are required")

    store = GapStore(DEFAULT_STATE)
    try:
        if decision == "clear":
            return {"ok": True, "cleared": store.clear(epd, color)}
        try:
            saved = store.set(
                epd, color, decision,
                reply=str(payload.get("reply") or ""),
                line=str(payload.get("line") or ""),
                opening=str(payload.get("opening") or ""),
            )
        except ValueError as err:
            raise HTTPException(400, str(err)) from err
    finally:
        store.close()

    progress = None
    if decision == "practising" and payload.get("answer_uci"):
        reviews = ReviewStore(DEFAULT_STATE)
        try:
            reviews.enrol(epd, color, uci=str(payload.get("answer_uci") or ""),
                          san=str(payload.get("answer_san") or ""),
                          opening=str(payload.get("opening") or ""),
                          line=str(payload.get("line") or ""))
            progress = reviews.progress()
        finally:
            reviews.close()
    return {"ok": True, "decision": saved, "progress": progress}


@app.get("/api/drills")
def drills_due(limit: int = 30) -> dict[str, Any]:
    """Positions ready to be seen again, plus how the player is doing overall."""
    store = ReviewStore(DEFAULT_STATE)
    try:
        return {"due": store.due(limit=limit), "progress": store.progress()}
    finally:
        store.close()


@app.post("/api/drills/enrol")
def enrol_drills(payload: dict[str, Any]) -> dict[str, Any]:
    """Take the positions from a finished report into the review cycle.

    Enrolling is idempotent: a position already being reviewed keeps its schedule, so
    re-running the analysis never wipes out progress.
    """
    positions = payload.get("positions") or []
    store = ReviewStore(DEFAULT_STATE)
    try:
        for pos in positions[:100]:
            epd = str(pos.get("epd") or "").strip()
            color = str(pos.get("color") or "").strip()
            if not epd or color not in ("white", "black"):
                continue
            store.enrol(epd, color, uci=str(pos.get("uci") or ""),
                        san=str(pos.get("san") or ""),
                        opening=str(pos.get("opening") or ""),
                        line=str(pos.get("line") or ""))
        return {"ok": True, "progress": store.progress()}
    finally:
        store.close()


@app.post("/api/drills/attempt")
def record_attempt(payload: dict[str, Any]) -> dict[str, Any]:
    """Grade one attempt and say when the position comes back."""
    epd = str(payload.get("epd") or "").strip()
    color = str(payload.get("color") or "").strip()
    if not epd or color not in ("white", "black"):
        raise HTTPException(400, "epd and a colour of white or black are required")

    cp_loss = payload.get("cp_loss")
    revealed = bool(payload.get("revealed"))
    grade = payload.get("grade")
    if grade is None:
        grade = grade_for_loss(float(cp_loss or 0), revealed=revealed)

    store = ReviewStore(DEFAULT_STATE)
    try:
        schedule = store.record(
            epd, color, str(payload.get("played_uci") or ""), int(grade),
            cp_loss=int(cp_loss) if cp_loss is not None else None,
        )
        return {
            "ok": True,
            "grade": int(grade),
            "due": describe_due(schedule),
            "repetitions": schedule.repetitions,
            "lapses": schedule.lapses,
            "progress": store.progress(),
        }
    finally:
        store.close()


@app.get("/api/history")
def history(limit: int = 20) -> dict[str, Any]:
    """Past runs and how the newest compares with the one before it."""
    store = HistoryStore(DEFAULT_STATE)
    try:
        return {"runs": store.runs(limit=limit), "comparison": store.compare_latest()}
    finally:
        store.close()


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "jobs": len(JOBS)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
