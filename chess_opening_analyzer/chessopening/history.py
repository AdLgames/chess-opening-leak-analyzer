"""Runs kept over time, so improvement is something the player can see.

A report on its own says what is wrong today. Two reports say whether last month's work
did anything — which is the only question that keeps somebody coming back. Each run stores
its headline figures and its flagged decisions, and comparing two of them answers "did I
fix it?" per line rather than in aggregate.

One caveat is built into the output rather than left implicit: two runs are only
comparable when they cover a similar number of games. A leak that vanished because the
player fixed it and a leak that vanished because this run read forty games instead of two
hundred look identical from the diff alone, so the run's game count travels with it and
the caller is told when the two differ enough to matter.
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from .marks import DEFAULT_STATE

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT NOT NULL DEFAULT 'local',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    player     TEXT NOT NULL DEFAULT '',
    source     TEXT NOT NULL DEFAULT '',
    games      INTEGER NOT NULL DEFAULT 0,
    leaks      INTEGER NOT NULL DEFAULT 0,
    lost_points REAL NOT NULL DEFAULT 0,
    options    TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS run_leaks (
    run_id   INTEGER NOT NULL,
    epd      TEXT NOT NULL,
    color    TEXT NOT NULL,
    uci      TEXT NOT NULL DEFAULT '',
    san      TEXT NOT NULL DEFAULT '',
    opening  TEXT NOT NULL DEFAULT '',
    line     TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    lost_points REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, epd, color, uci)
);
CREATE INDEX IF NOT EXISTS run_leaks_run ON run_leaks (run_id);
"""

# How different two runs' game counts may be before the comparison stops being fair.
COMPARABLE_RATIO = 0.6


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (row["epd"], row["color"], row["uci"])


class HistoryStore:
    """Past runs, alongside the player's other state."""

    def __init__(self, path: str = DEFAULT_STATE, user_id: str = "local"):
        self.path = path
        self.user_id = user_id
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    def save_run(self, summary: dict[str, Any], rows: list[dict[str, Any]],
                 player: str = "", source: str = "", options: dict | None = None) -> int:
        cur = self.con.execute(
            "INSERT INTO runs (user_id, player, source, games, leaks, lost_points, options) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, player, source, int(summary.get("games", 0)),
             int(summary.get("leaks", 0)), _f(summary.get("lost_points")),
             json.dumps(options or {})),
        )
        run_id = int(cur.lastrowid)
        self.con.executemany(
            "INSERT OR REPLACE INTO run_leaks (run_id, epd, color, uci, san, opening, line, "
            "category, lost_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (run_id, " ".join(str(r.get("fen", "")).split()[:4]), r.get("player_color", ""),
                 r.get("your_move_uci", ""), r.get("your_move", ""),
                 r.get("opening", "") or r.get("eco", ""), r.get("variation_line", ""),
                 r.get("category", ""), _f(r.get("lost_points")))
                for r in rows
            ],
        )
        self.con.commit()
        return run_id

    def runs(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.con.execute(
            "SELECT * FROM runs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (self.user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def leaks_for(self, run_id: int) -> list[dict[str, Any]]:
        rows = self.con.execute(
            "SELECT * FROM run_leaks WHERE run_id = ? ORDER BY lost_points DESC", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def compare_latest(self) -> dict[str, Any] | None:
        """The newest run against the one before it, or None if there is no pair yet."""
        recent = self.runs(limit=2)
        if len(recent) < 2:
            return None
        current, previous = recent[0], recent[1]
        return diff_runs(
            previous, self.leaks_for(previous["id"]),
            current, self.leaks_for(current["id"]),
        )

    def close(self) -> None:
        self.con.close()


def diff_runs(
    previous: dict[str, Any], previous_leaks: list[dict[str, Any]],
    current: dict[str, Any], current_leaks: list[dict[str, Any]],
    worse_by: float = 0.2,
) -> dict[str, Any]:
    """What changed between two runs, per line rather than in aggregate.

    `worse_by` is the fraction a line's cost must move before it counts as a real change:
    without it, ordinary variance between two runs reads as a trend.
    """
    before = {_key(r): r for r in previous_leaks}
    after = {_key(r): r for r in current_leaks}

    fixed = [r for k, r in before.items() if k not in after]
    appeared = [r for k, r in after.items() if k not in before]
    worse, better, unchanged = [], [], 0
    for key, now in after.items():
        was = before.get(key)
        if was is None:
            continue
        then_cost, now_cost = _f(was["lost_points"]), _f(now["lost_points"])
        if then_cost and now_cost > then_cost * (1 + worse_by):
            worse.append({**now, "was": then_cost})
        elif then_cost and now_cost < then_cost * (1 - worse_by):
            better.append({**now, "was": then_cost})
        else:
            unchanged += 1

    for group in (fixed, appeared, worse, better):
        group.sort(key=lambda r: -_f(r["lost_points"]))

    games_before = int(previous.get("games") or 0)
    games_now = int(current.get("games") or 0)
    comparable = bool(
        games_before and games_now
        and min(games_before, games_now) / max(games_before, games_now) >= COMPARABLE_RATIO
    )

    return {
        "previous": {"id": previous.get("id"), "created_at": previous.get("created_at"),
                     "games": games_before, "leaks": previous.get("leaks"),
                     "lost_points": _f(previous.get("lost_points"))},
        "current": {"id": current.get("id"), "created_at": current.get("created_at"),
                    "games": games_now, "leaks": current.get("leaks"),
                    "lost_points": _f(current.get("lost_points"))},
        "fixed": fixed,
        "new": appeared,
        "worse": worse,
        "better": better,
        "unchanged": unchanged,
        "points_recovered": round(sum(_f(r["lost_points"]) for r in fixed), 2),
        "comparable": comparable,
        "headline": _headline(fixed, appeared, comparable, games_before, games_now),
    }


def _headline(fixed: list[dict[str, Any]], appeared: list[dict[str, Any]],
              comparable: bool, games_before: int, games_now: int) -> str:
    """The comparison in one sentence, including when it should not be trusted."""
    if not comparable:
        return (
            f"This run read {games_now} games and the last read {games_before}, which is too "
            "different to compare fairly. Run the same number to see what actually changed."
        )
    recovered = round(sum(_f(r["lost_points"]) for r in fixed), 1)
    if fixed and not appeared:
        gone = ("One of your leaks is gone" if len(fixed) == 1
                else f"{len(fixed)} of your leaks are gone")
        return f"{gone} since last time, worth about {recovered} points. Nothing new appeared."
    if fixed and appeared:
        return (
            f"{len(fixed)} gone (about {recovered} points recovered), {len(appeared)} new. "
            "Net progress depends on which mattered more."
        )
    if appeared:
        return f"{len(appeared)} new leaks since last time, and none of the old ones cleared."
    return "Nothing changed since your last run."
