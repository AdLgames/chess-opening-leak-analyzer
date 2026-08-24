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
from chessopening.board import (BoardError, cp_text, engine_lines,  # noqa: E402
                                position_payload)
from chessopening.engine import find_engine  # noqa: E402
from chessopening.ingest import (FetchOptions, IngestError, fetch_games,  # noqa: E402
                                 lookup_player, provider_label, speeds_from_csv)
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
    "max_fetch_games": 120,
    "max_board_depth": 12,
    "max_board_multipv": 3,
}

# board evaluations are cached in /tmp, the only writable path on the function
BOARD_CACHE = os.path.join(WORK_ROOT, "board_evals.json")
_BOARD_DB: LocalOpeningDatabase | None = None


def board_db() -> LocalOpeningDatabase | None:
    """One shared read-only book handle for the board panes, safe across threads."""
    global _BOARD_DB  # noqa: PLW0603 - deliberate module-level singleton
    if _BOARD_DB is None and os.path.exists(DEFAULT_DB):
        import sqlite3

        _BOARD_DB = LocalOpeningDatabase(DEFAULT_DB)
        _BOARD_DB.con.close()
        _BOARD_DB.con = sqlite3.connect(DEFAULT_DB, check_same_thread=False)
        _BOARD_DB.con.row_factory = sqlite3.Row
    return _BOARD_DB

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
        "ingest": {"providers": ["chesscom", "lichess"], "default_provider": "chesscom",
                   "max_games": LIMITS["max_fetch_games"],
                   "speeds": ["bullet", "blitz", "rapid", "classical", "daily"]},
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
    source: str = Form(""),
    username: str = Form(""),
    provider: str = Form("chesscom"),
    max_games: int = Form(120),
    time_classes: str = Form("blitz,rapid,classical"),
    include_unrated: str = Form("false"),
    since: str = Form(""),
    until: str = Form(""),
    lichess_token: str = Form(""),
    refresh: str = Form("false"),
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
    sample = use_sample.lower() == "true" or source == "sample"
    by_username = source == "username" or (bool(username.strip()) and not sample and not source)
    work = tempfile.mkdtemp(prefix="run-", dir=WORK_ROOT)
    account: dict[str, Any] | None = None

    try:
        if by_username:
            wanted = int(max_games)
            if wanted > LIMITS["max_fetch_games"]:
                notes.append(f"games to read clamped to {LIMITS['max_fetch_games']} "
                             "on the hosted deployment")
                wanted = int(LIMITS["max_fetch_games"])
            try:
                fetched = fetch_games(
                    FetchOptions(
                        provider=provider,
                        username=username.strip(),
                        max_games=wanted,
                        speeds=speeds_from_csv(time_classes),
                        rated_only=include_unrated.lower() != "true",
                        since=since.strip() or None,
                        until=until.strip() or None,
                        token=lichess_token.strip() or None,
                        # the function filesystem is ephemeral, so /tmp is the only cache
                        cache_dir=os.path.join(WORK_ROOT, "archives"),
                        refresh=refresh.lower() == "true",
                        timeout=15.0,
                    ),
                    progress=lambda msg: log.append(str(msg)),
                )
            except IngestError as exc:
                detail = str(exc)
                if exc.hint:
                    detail += f" {exc.hint}"
                raise HTTPException(400, detail) from exc
            pgn_dir = fetched.pgn_dir
            player = player or fetched.username
            account = {"provider": fetched.provider, "username": fetched.username,
                       "label": provider_label(fetched.provider), "games": fetched.games}
            notes.extend(fetched.notes)
        elif sample:
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
            "account": account,
            "source": "username" if by_username else ("sample" if sample else "upload"),
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


@app.get("/api/lookup")
def lookup(provider: str = "chesscom", username: str = "") -> dict[str, Any]:
    try:
        return {"found": True, "profile": lookup_player(provider, username, timeout=12.0)}
    except IngestError as exc:
        return {"found": False, "error": str(exc), "hint": exc.hint}


@app.get("/api/position")
def position(fen: str = "", moves: str = "", san: str = "", book: str = "true") -> dict[str, Any]:
    """Legal moves, naming and book statistics for one position.

    `san` replays a report line so the opening name and move numbers are real;
    `moves` is a comma-separated UCI list applied on top, which keeps legality
    checking on the server rather than trusting the browser.
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
    """Stockfish's top continuations for the position on screen, at hosted depth."""
    fen = str(payload.get("fen") or "").strip()
    if not fen:
        raise HTTPException(400, "fen is required")
    if not ENGINE_PATH:
        raise HTTPException(503, "No engine available in this deployment")
    depth = max(6, min(int(payload.get("depth") or 12), LIMITS["max_board_depth"]))
    multipv = max(1, min(int(payload.get("multipv") or 3), LIMITS["max_board_multipv"]))
    try:
        result = engine_lines(
            fen,
            depth=depth,
            multipv=multipv,
            pv_len=max(1, min(int(payload.get("pv_len") or 6), 8)),
            engine_path=ENGINE_PATH,
            cache_path=BOARD_CACHE,
        )
    except FileNotFoundError as exc:
        raise HTTPException(503, f"No engine available: {exc}") from exc
    except BoardError as exc:
        raise HTTPException(400, str(exc)) from exc
    for line in result.get("lines", []):
        line["eval"] = cp_text(line.get("cp"))
    result["capped"] = {"depth": LIMITS["max_board_depth"], "multipv": LIMITS["max_board_multipv"]}
    return result


@app.get("/api/openings")
def openings(q: str = "", limit: int = 30) -> dict[str, Any]:
    """Named openings from the bundled book, for the library search box."""
    db = board_db()
    if db is None:
        raise HTTPException(503, "No local opening database installed")
    return {"query": q, "results": db.search_openings(q, max(1, min(int(limit), 100)))}


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "engine": bool(ENGINE_PATH), "serverless": True}


# On Vercel the CDN serves `public/`, so this mount never sees traffic there. Locally it
# makes `uvicorn api.index:app` a complete preview of the hosted build on one port.
_PUBLIC = os.path.join(ROOT, "public")
if os.path.isdir(_PUBLIC):
    from fastapi.staticfiles import StaticFiles  # noqa: PLC0415

    app.mount("/", StaticFiles(directory=_PUBLIC, html=True), name="public")
