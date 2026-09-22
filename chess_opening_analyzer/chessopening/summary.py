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


def family_of(name: str) -> str:
    """The opening family a variation belongs to.

    ECO names are "Family: Variation, Sub-variation", so the part before the
    first colon is the thing a player would say they play. Without this roll-up
    "Italian Game: Giuoco Piano" and "Italian Game: Giuoco Pianissimo" are two
    unrelated rows, and a repertoire-wide problem reads as several small ones.
    """
    text = (name or "").strip()
    if not text:
        return "Unclassified"
    return text.split(":", 1)[0].strip() or text


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
    profiles = stats.get("opening_profiles") or {}
    families = _by_family(rows)

    return {
        "games": stats["games"],
        "decisions": stats["nodes"],
        "judged": stats["repeated"],
        # every game-appearance behind a judged decision: the denominator of coverage
        "judged_games": stats.get("repeated_games", 0),
        # Who the book compared them against. A score gap means something quite
        # different depending on whose games set the baseline, so the figure
        # should never be read without it.
        "band": stats.get("player_band_label", ""),
        "banded": bool(stats.get("book_has_bands")),
        # how many repeated decisions were examined at all, so "24 leaks" can be
        # read as a share of what you play rather than as a bare count
        "tree_rows": stats.get("tree_rows", 0),
        "clean": max(0, int(stats.get("tree_rows", 0)) - len(rows)),
        "leaks": len(rows),
        "lost_points": round(sum(_f(r["lost_points"]) for r in rows), 2),
        "cost": round(sum(_f(r.get("cost")) for r in rows), 2),
        "blunders": sum(1 for r in rows if _f(r["eval_drop_pawns"]) >= 0.8),
        "flags": dict(flags),
        "by_opening": openings[:12],
        # The same rows one level up: family, then the variations inside it.
        # Ranked by cost rather than points shed, because points shed is the raw
        # figure — a family whose whole case rests on one thin sample would
        # otherwise outrank one seen thirty times, which is the thing the cost
        # shrinkage exists to prevent at node level and did not at this one.
        "by_family": families[:12],
        # everything the openings explorer needs: one profile per opening, the
        # run-wide spread of break points, and the traps this player walks into
        "explorer": {
            "openings": profiles.get("openings", []),
            "break_moves": profiles.get("break_moves", []),
            "worst_against": profiles.get("worst_against", []),
            "traps": stats.get("traps", {}),
        },
        "white_leaks": sum(1 for r in rows if r["player_color"] == "white"),
        "black_leaks": sum(1 for r in rows if r["player_color"] == "black"),
        "top": rows[0] if rows else None,
    }


def _by_family(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Leaks rolled up per family, each carrying its own variations."""
    fams: dict[str, dict[str, Any]] = {}
    for r in rows:
        name = r.get("opening") or r.get("eco") or "Unclassified"
        fam = fams.setdefault(family_of(name), {
            "family": family_of(name), "cost": 0.0, "lost_points": 0.0,
            "leaks": 0, "games": 0, "_vars": {},
        })
        var = fam["_vars"].setdefault(name, {
            "opening": name, "eco": r.get("eco") or "", "cost": 0.0,
            "lost_points": 0.0, "leaks": 0, "games": 0,
        })
        for bucket in (fam, var):
            bucket["cost"] += _f(r.get("cost"))
            bucket["lost_points"] += _f(r.get("lost_points"))
            bucket["leaks"] += 1
            bucket["games"] += int(_f(r.get("your_games")))

    out = []
    for fam in fams.values():
        variations = sorted(fam.pop("_vars").values(), key=lambda v: -v["cost"])
        for v in variations:
            v["cost"] = round(v["cost"], 2)
            v["lost_points"] = round(v["lost_points"], 2)
        out.append({**fam, "cost": round(fam["cost"], 2),
                    "lost_points": round(fam["lost_points"], 2),
                    "variations": variations})
    out.sort(key=lambda d: -d["cost"])
    return out
