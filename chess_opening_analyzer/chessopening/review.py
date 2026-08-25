"""Spaced repetition over the positions a player got wrong.

One graded attempt is a quiz. Remembering an opening is built by recalling the same line
again days later, and again after that, with the gap widening each time you get it right
and collapsing when you do not. That is what turns "I read the fix" into "I play the fix".

Two clocks run at once, and they are not the same thing:

  within the session   a position you just missed comes back before you finish, because
                       the answer is still in front of you and repeating it now is what
                       makes it stick at all.
  across days          a position you got right recedes — one day, then six, then longer —
                       and one you missed returns tomorrow.

The day-scale schedule is SM-2, the algorithm behind most flashcard software: an ease
factor per position that rises when recall is easy and falls when it is not, multiplying
the interval each time. It is old, simple, and good enough that the interesting work is in
grading chess moves rather than in the arithmetic.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any

from .marks import DEFAULT_STATE

SCHEMA = """
CREATE TABLE IF NOT EXISTS drill_state (
    user_id  TEXT NOT NULL DEFAULT 'local',
    epd      TEXT NOT NULL,
    color    TEXT NOT NULL,
    uci      TEXT NOT NULL DEFAULT '',   -- the move that was being taught
    san      TEXT NOT NULL DEFAULT '',
    opening  TEXT NOT NULL DEFAULT '',
    line     TEXT NOT NULL DEFAULT '',
    ease     REAL NOT NULL DEFAULT 2.5,
    interval_days REAL NOT NULL DEFAULT 0,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    lapses        INTEGER NOT NULL DEFAULT 0,
    due_at   TEXT NOT NULL,
    last_grade INTEGER,
    last_seen  TEXT,
    PRIMARY KEY (user_id, epd, color)
);
CREATE TABLE IF NOT EXISTS drill_attempts (
    user_id TEXT NOT NULL DEFAULT 'local',
    epd     TEXT NOT NULL,
    color   TEXT NOT NULL,
    played_uci TEXT NOT NULL DEFAULT '',
    grade   INTEGER NOT NULL,
    cp_loss INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS drill_attempts_pos ON drill_attempts (user_id, epd, color);
"""

# How a move played in a drill becomes an SM-2 grade. The thresholds match the verdicts the
# practice pane already shows, so what the player is told and what the schedule believes
# never disagree.
GRADE_BEST = 5      # within 20cp of the engine's pick
GRADE_GOOD = 4      # within 60cp: as good as best for practical purposes
GRADE_OK = 3        # within 150cp: playable, and still counts as recalled
GRADE_WEAK = 2      # worse than that: this is a lapse
GRADE_REVEALED = 1  # asked to be shown the answer

PASSING = GRADE_OK  # at or above this, the position is considered recalled


def grade_for_loss(cp_loss: float, revealed: bool = False) -> int:
    """Turn centipawns given away into a recall grade.

    Being shown the answer is always a lapse, however good the move would have been —
    recognising a move is not the same as recalling it.
    """
    if revealed:
        return GRADE_REVEALED
    if cp_loss <= 20:
        return GRADE_BEST
    if cp_loss <= 60:
        return GRADE_GOOD
    if cp_loss <= 150:
        return GRADE_OK
    return GRADE_WEAK


@dataclass(frozen=True)
class Schedule:
    """Where one position stands in the review cycle."""

    ease: float = 2.5
    interval_days: float = 0.0
    repetitions: int = 0
    lapses: int = 0
    due_at: datetime | None = None


def next_schedule(state: Schedule, grade: int, now: datetime | None = None) -> Schedule:
    """The position's new place in the queue after one attempt.

    SM-2, with one deliberate change: a lapse comes back tomorrow rather than being reset
    to a fresh card. The player has seen this line before and the point is to repair it,
    not to pretend they are meeting it for the first time.
    """
    now = now or datetime.now(timezone.utc)
    grade = max(0, min(5, int(grade)))

    # Ease drifts with how hard recall was, and never falls below the SM-2 floor — past
    # that point the interval stops growing at all and the position just churns.
    ease = state.ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    ease = max(1.3, round(ease, 3))

    if grade < PASSING:
        return Schedule(
            ease=ease,
            interval_days=1.0,
            repetitions=0,
            lapses=state.lapses + 1,
            due_at=now + timedelta(days=1),
        )

    repetitions = state.repetitions + 1
    if repetitions == 1:
        interval = 1.0
    elif repetitions == 2:
        interval = 6.0
    else:
        interval = round(state.interval_days * ease, 2)
    return Schedule(
        ease=ease,
        interval_days=interval,
        repetitions=repetitions,
        lapses=state.lapses,
        due_at=now + timedelta(days=interval),
    )


def requeue_within_session(queue: list[Any], index: int, gap: int = 3) -> list[Any]:
    """Move a missed position further down the current session rather than dropping it.

    `gap` positions later, or the end of the queue if that is sooner — far enough that the
    answer is not simply still on screen, near enough to be the same sitting.
    """
    if not queue or not 0 <= index < len(queue):
        return queue
    item = queue[index]
    rest = queue[:index] + queue[index + 1:]
    target = min(index + gap, len(rest))
    return rest[:target] + [item] + rest[target:]


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class ReviewStore:
    """Attempts and schedules, in the same file as the player's other decisions."""

    def __init__(self, path: str = DEFAULT_STATE, user_id: str = "local"):
        self.path = path
        self.user_id = user_id
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    # -------- reading --------
    def schedule_for(self, epd: str, color: str) -> Schedule:
        row = self.con.execute(
            "SELECT ease, interval_days, repetitions, lapses, due_at FROM drill_state "
            "WHERE user_id = ? AND epd = ? AND color = ?",
            (self.user_id, epd, color),
        ).fetchone()
        if row is None:
            return Schedule()
        return Schedule(
            ease=row["ease"], interval_days=row["interval_days"],
            repetitions=row["repetitions"], lapses=row["lapses"],
            due_at=_parse(row["due_at"]),
        )

    def due(self, now: datetime | None = None, limit: int = 30) -> list[dict[str, Any]]:
        """Positions ready to be seen again, the most overdue first."""
        now = now or datetime.now(timezone.utc)
        rows = self.con.execute(
            "SELECT * FROM drill_state WHERE user_id = ? AND due_at <= ? "
            "ORDER BY due_at ASC LIMIT ?",
            (self.user_id, _iso(now), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def progress(self, now: datetime | None = None) -> dict[str, Any]:
        """How the player is doing, in the terms the dashboard reports."""
        now = now or datetime.now(timezone.utc)
        total = self.con.execute(
            "SELECT COUNT(*) FROM drill_state WHERE user_id = ?", (self.user_id,)
        ).fetchone()[0]
        due = self.con.execute(
            "SELECT COUNT(*) FROM drill_state WHERE user_id = ? AND due_at <= ?",
            (self.user_id, _iso(now)),
        ).fetchone()[0]
        # "Known" is deliberately a high bar: recalled three times running, with the gap
        # now measured in weeks. Anything less is still being learned.
        known = self.con.execute(
            "SELECT COUNT(*) FROM drill_state WHERE user_id = ? AND repetitions >= 3 "
            "AND interval_days >= 14",
            (self.user_id,),
        ).fetchone()[0]
        attempts = self.con.execute(
            "SELECT COUNT(*) AS n, SUM(grade >= ?) AS passed FROM drill_attempts "
            "WHERE user_id = ?", (PASSING, self.user_id),
        ).fetchone()
        n = attempts["n"] or 0
        passed = attempts["passed"] or 0
        return {
            "tracked": total,
            "due": due,
            "known": known,
            "learning": total - known,
            "attempts": n,
            "accuracy_pct": round(100 * passed / n, 1) if n else None,
        }

    def history(self, epd: str, color: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.con.execute(
            "SELECT played_uci, grade, cp_loss, created_at FROM drill_attempts "
            "WHERE user_id = ? AND epd = ? AND color = ? ORDER BY created_at DESC LIMIT ?",
            (self.user_id, epd, color, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # -------- writing --------
    def enrol(self, epd: str, color: str, uci: str = "", san: str = "",
              opening: str = "", line: str = "", now: datetime | None = None) -> None:
        """Start tracking a position, due immediately. Existing schedules are left alone."""
        now = now or datetime.now(timezone.utc)
        self.con.execute(
            "INSERT INTO drill_state (user_id, epd, color, uci, san, opening, line, due_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, epd, color) DO UPDATE SET "
            "  uci = excluded.uci, san = excluded.san, opening = excluded.opening, "
            "  line = excluded.line",
            (self.user_id, epd, color, uci, san, opening, line, _iso(now)),
        )
        self.con.commit()

    def record(self, epd: str, color: str, played_uci: str, grade: int,
               cp_loss: int | None = None, now: datetime | None = None) -> Schedule:
        """Log an attempt and move the position along the schedule."""
        now = now or datetime.now(timezone.utc)
        updated = next_schedule(self.schedule_for(epd, color), grade, now)
        self.con.execute(
            "INSERT INTO drill_attempts (user_id, epd, color, played_uci, grade, cp_loss, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, epd, color, played_uci, int(grade), cp_loss, _iso(now)),
        )
        self.con.execute(
            "INSERT INTO drill_state (user_id, epd, color, ease, interval_days, repetitions, "
            "  lapses, due_at, last_grade, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, epd, color) DO UPDATE SET "
            "  ease = excluded.ease, interval_days = excluded.interval_days, "
            "  repetitions = excluded.repetitions, lapses = excluded.lapses, "
            "  due_at = excluded.due_at, last_grade = excluded.last_grade, "
            "  last_seen = excluded.last_seen",
            (self.user_id, epd, color, updated.ease, updated.interval_days,
             updated.repetitions, updated.lapses, _iso(updated.due_at or now),
             int(grade), _iso(now)),
        )
        self.con.commit()
        return updated

    def forget(self, epd: str, color: str) -> bool:
        """Stop tracking a position — its history goes too."""
        cur = self.con.execute(
            "DELETE FROM drill_state WHERE user_id = ? AND epd = ? AND color = ?",
            (self.user_id, epd, color),
        )
        self.con.execute(
            "DELETE FROM drill_attempts WHERE user_id = ? AND epd = ? AND color = ?",
            (self.user_id, epd, color),
        )
        self.con.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self.con.close()


def describe_due(schedule: Schedule, now: datetime | None = None) -> str:
    """When this position comes back, in words rather than a timestamp."""
    if schedule.due_at is None:
        return "due now"
    now = now or datetime.now(timezone.utc)
    days = (schedule.due_at - now).total_seconds() / 86400
    if days < 0.5:
        return "again today"
    if days < 1.5:
        return "again tomorrow"
    if days < 14:
        return f"again in {round(days)} days"
    if days < 60:
        return f"again in {round(days / 7)} weeks"
    return f"again in {round(days / 30)} months"


__all__ = [
    "GRADE_BEST", "GRADE_GOOD", "GRADE_OK", "GRADE_WEAK", "GRADE_REVEALED", "PASSING",
    "ReviewStore", "Schedule", "describe_due", "grade_for_loss", "next_schedule",
    "requeue_within_session", "replace",
]
