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


def group_by_line(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Collapse flagged decisions into one entry per line, keyed on the earliest mistake.

    A bad move at move 6 drags the rest of the line down with it, so the same hole comes
    back as separate rows at moves 8, 10 and 12, each competing for the top of the report.
    A row whose line begins with another row's line is downstream of it — the player had
    already played the earlier move to get there — so it is nested underneath instead of
    standing on its own.

    Fixing the headline move makes the whole branch moot, which is why the group carries the
    branch's combined cost rather than only the first row's.
    """
    ordered = sorted(rows, key=lambda r: (int(_f(r.get("ply")) or 0), -_f(r.get("priority"))))
    groups: list[dict[str, Any]] = []

    for row in ordered:
        line = (row.get("variation_line") or "").split()
        parent = None
        for group in groups:
            head = group["_line"]
            # Same colour only: White's move 6 does not cause Black's move 8.
            if (
                len(head) < len(line)
                and line[: len(head)] == head
                and group["headline"]["player_color"] == row["player_color"]
            ):
                # Only roots are in `groups` — a group whose line extended another would
                # itself have been nested — so the first match is the only one.
                parent = group
                break
        if parent is not None:
            parent["downstream"].append(row)
        else:
            groups.append({"_line": line, "headline": row, "downstream": []})

    for group in groups:
        branch = [group["headline"], *group["downstream"]]
        head = group["headline"]
        group.pop("_line")
        group["lost_points"] = round(sum(_f(r.get("lost_points")) for r in branch), 2)
        group["lost_points_conservative"] = round(
            sum(_f(r.get("lost_points_conservative")) for r in branch), 2
        )
        group["priority"] = round(sum(_f(r.get("priority")) for r in branch), 2)
        group["followers"] = len(group["downstream"])
        # Both halves of why this group ranks where it does: how often it happens, and
        # what it costs each time. One number alone cannot tell the reader which it is.
        group["games"] = sum(int(_f(r.get("your_games")) or 0) for r in branch)
        group["cost_per_game"] = round(group["lost_points"] / group["games"], 2) if group["games"] else 0.0
        group["opening"] = head.get("opening") or head.get("eco") or "Unclassified"
        group["explanation"] = head.get("explanation", "")
        group["player_color"] = head.get("player_color", "")

    groups.sort(key=lambda g: -g["priority"])
    return groups


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
        "groups": group_by_line(rows),
        # Lines the player will meet but has barely played: absent from `rows` by
        # construction, since the report can only see moves that were actually made.
        "coverage": stats.get("coverage", [])[:12],
        "tree": stats.get("tree", {}),
        "tree_totals": stats.get("tree_totals", {}),
        "coverage_total": len(stats.get("coverage", [])),
        "white_leaks": sum(1 for r in rows if r["player_color"] == "white"),
        "black_leaks": sum(1 for r in rows if r["player_color"] == "black"),
        "top": rows[0] if rows else None,
        # Who they were measured against. Carried through so the dashboard never has to
        # leave "the book scores 54%" meaning whatever the reader assumes it means.
        "player_rating": stats.get("player_rating"),
        "player_band_label": stats.get("player_band_label", "all ratings"),
        "book_has_bands": bool(stats.get("book_has_bands")),
    }
