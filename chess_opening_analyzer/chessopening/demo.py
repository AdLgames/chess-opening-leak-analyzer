"""The demo report: a finished run over the bundled sample archive.

The demo exists so a first-time visitor can see a populated report in one click.
Waiting out a real engine pass would defeat that, so the payload is cached: a
baked file committed next to the deployment if there is one, otherwise a copy
written to the work directory the first time it is asked for.

`tools/bake_demo_report.py` writes the baked file.
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
from typing import Any

from .analyze import analyze
from .pgn_loader import detect_main_player, find_pgn_files
from .summary import summarise

#: Settings the demo always runs with, whatever the user last chose.
DEMO_OPTIONS: dict[str, Any] = {
    "depth": 12,
    "color": "both",
    "max_moves": 15,
    "min_games": 3,
    "eval_drop": 0.8,
    "score_gap": 6.0,
    "min_db_games": 20,
    "multipv": 3,
    "no_engine": False,
}


def _csv_text(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def build_demo_report(
    sample_dir: str,
    out_dir: str,
    *,
    engine_budget_s: float | None = None,
    max_games: int | None = None,
    cache_dir: str | None = None,
) -> dict[str, Any]:
    """Run the pipeline over the sample archive and return a report payload."""
    files = find_pgn_files(sample_dir)
    if not files:
        raise FileNotFoundError(f"no sample archive in {sample_dir}")
    player = detect_main_player(files)
    if not player:
        raise ValueError("could not detect the sample player")
    started = time.time()
    log: list[str] = []
    opts = dict(DEMO_OPTIONS)
    result = analyze(
        pgn_dir=sample_dir,
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
        # The sample archive is nobody's games, so nobody's decisions apply to it —
        # and the deployment that serves it has a read-only filesystem to not go
        # looking on.
        no_marks=True,
        max_games=max_games,
        engine_budget_s=engine_budget_s,
        cache_dir=cache_dir or os.path.join(out_dir, "_cache"),
        log=lambda *parts: log.append(" ".join(str(p) for p in parts)),
    )
    with open(result["report"], encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {
        "player": player,
        "summary": summarise(rows, result),
        "rows": rows,
        "log": log[-40:],
        "notes": list(result.get("notes", [])),
        "elapsed": round(time.time() - started, 1),
        "options": opts,
        "csv": _csv_text(rows),
        "source": "sample",
        "demo": True,
    }


def load_or_build_demo(
    sample_dir: str,
    out_dir: str,
    *,
    baked_paths: tuple[str, ...] = (),
    cache_path: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """The demo payload, from the first cache that has it, computing it if none does."""
    for path in (*baked_paths, *( (cache_path,) if cache_path else () )):
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    payload = json.load(fh)
                payload["demo"] = True
                payload["cached"] = True
                return payload
            except (OSError, ValueError):
                pass  # a truncated cache is not worth failing the demo over
    payload = build_demo_report(sample_dir, out_dir, **kwargs)
    if cache_path:
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            tmp = cache_path + ".part"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            os.replace(tmp, cache_path)
        except OSError:
            pass  # read-only filesystem: the demo still works, it just recomputes
    return payload
