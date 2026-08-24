"""Roll a flagged-decision CSV up into the shape the dashboards render.

Shared by the local FastAPI server and the Vercel serverless function so both
report identical numbers.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def summarise(rows: list[dict[str, str]], stats: dict[str, Any]) -> dict[str, Any]:
    """Aggregate flagged rows by opening and count the flags.

    `rows` are CSV records from `analyze()`; `stats` is its return value.
    """
    by_opening: dict[str, dict[str, float]] = defaultdict(
        lambda: {"lost_points": 0.0, "leaks": 0, "games": 0, "score": 0.0, "db_score": 0.0, "n": 0}
    )
    flags: dict[str, int] = defaultdict(int)
    for r in rows:
        key = r["opening"] or r["eco"] or "Unclassified"
        b = by_opening[key]
        b["lost_points"] += _f(r["lost_points"])
        b["leaks"] += 1
        b["games"] += int(_f(r["your_games"]))
        b["score"] += _f(r["your_score_pct"])
        b["db_score"] += _f(r["db_move_score_pct"]) or _f(r["db_position_score_pct"])
        b["n"] += 1
        for fl in (r["flag"] or "").split("+"):
            if fl:
                flags[fl] += 1

    openings = [
        {"opening": k, "lost_points": round(v["lost_points"], 2), "leaks": int(v["leaks"]),
         "games": int(v["games"]), "your_score": round(v["score"] / max(1, v["n"]), 1),
         "db_score": round(v["db_score"] / max(1, v["n"]), 1)}
        for k, v in by_opening.items()
    ]
    openings.sort(key=lambda d: -d["lost_points"])

    return {
        "games": stats["games"],
        "decisions": stats["nodes"],
        "judged": stats["repeated"],
        "leaks": len(rows),
        "lost_points": round(sum(_f(r["lost_points"]) for r in rows), 2),
        "blunders": sum(1 for r in rows if _f(r["eval_drop_pawns"]) >= 0.8),
        "flags": dict(flags),
        "by_opening": openings[:12],
        "white_leaks": sum(1 for r in rows if r["player_color"] == "white"),
        "black_leaks": sum(1 for r in rows if r["player_color"] == "black"),
        "top": rows[0] if rows else None,
    }
