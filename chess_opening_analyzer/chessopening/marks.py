"""What the player has decided, so the report stops arguing with them.

A tool that keeps flagging a move you have deliberately chosen is a tool you stop
believing. If someone plays the Italian on purpose, being told every month that the book
scores better with the Ruy Lopez is noise — they know, and they have chosen.

So a decision can be recorded against a position:

    committed  this is my move; judge the position, not the choice
    ignored    I have seen this finding and do not want it again

Committing does *not* silence everything. A move that hangs a piece is still reported,
because that is a fact about the position rather than a matter of taste — "unless they're
objectively problematic" is exactly the line. What committing removes is the *results*
argument: the win-rate comparison and the popularity complaint, both of which are really
saying "most people prefer something else".

Local-first with a single implicit user, matching the data model sketched in the phase 2
requirements. The same schema carries over when accounts arrive; only the `user_id` column
turns from a constant into a real one.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable

# Deliberately not under ~/.cache: this is what the player has told us, and a cache is by
# definition something you can throw away.
DEFAULT_STATE = os.environ.get(
    "LEAKLAB_STATE", os.path.expanduser("~/.local/share/leaklab/repertoire.sqlite")
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS repertoire_marks (
    user_id TEXT NOT NULL DEFAULT 'local',
    epd     TEXT NOT NULL,
    color   TEXT NOT NULL,          -- the side the player was on
    uci     TEXT NOT NULL,          -- the move they committed to, or the one being ignored
    san     TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL,         -- 'committed' | 'ignored'
    note    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, epd, color)
);
"""

DECISIONS = ("committed", "ignored")

# A gap is a different kind of decision from a mark. A mark is about a move the player
# made; a gap is about a reply they have never had to answer, so there is no move of
# theirs to attach it to and the two must not share a primary key.
GAP_SCHEMA = """
CREATE TABLE IF NOT EXISTS gap_decisions (
    user_id  TEXT NOT NULL DEFAULT 'local',
    epd      TEXT NOT NULL,          -- the position after the reply they must answer
    color    TEXT NOT NULL,
    reply    TEXT NOT NULL DEFAULT '',   -- the opponent move that gets there, for display
    line     TEXT NOT NULL DEFAULT '',
    opening  TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL,          -- 'learning' | 'practising' | 'ignored'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, epd, color)
);
"""

GAP_DECISIONS = ("learning", "practising", "ignored")


@dataclass(frozen=True)
class Mark:
    epd: str
    color: str
    uci: str
    san: str
    decision: str
    note: str = ""


def filter_flags(flags: list[str], mark: Mark | None, played_uci: str) -> list[str] | None:
    """The flags that survive the player's own decision about this position.

    Returns None when the finding should not be reported at all. A mark only applies to
    the move it was made about — switching to a different move is a new choice, and gets
    judged on its own.
    """
    if mark is None or mark.uci != played_uci:
        return flags
    if mark.decision == "ignored":
        return None
    if mark.decision == "committed":
        # Keep only what is true regardless of preference. The win-rate and popularity
        # flags are arguments about taste, and the player has already had that argument.
        kept = [f for f in flags if f == "EVAL_DROP"]
        return kept or None
    return flags


class MarkStore:
    """Read and write the player's decisions. Missing file means no decisions yet."""

    def __init__(self, path: str = DEFAULT_STATE, user_id: str = "local"):
        self.path = path
        self.user_id = user_id
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    def set(self, epd: str, color: str, uci: str, decision: str, san: str = "", note: str = "") -> Mark:
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}, got {decision!r}")
        self.con.execute(
            "INSERT INTO repertoire_marks (user_id, epd, color, uci, san, decision, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, epd, color) DO UPDATE SET "
            "  uci = excluded.uci, san = excluded.san, decision = excluded.decision, "
            "  note = excluded.note, created_at = datetime('now')",
            (self.user_id, epd, color, uci, san, decision, note),
        )
        self.con.commit()
        return Mark(epd=epd, color=color, uci=uci, san=san, decision=decision, note=note)

    def clear(self, epd: str, color: str) -> bool:
        """Undo a decision. Returns whether there was one."""
        cur = self.con.execute(
            "DELETE FROM repertoire_marks WHERE user_id = ? AND epd = ? AND color = ?",
            (self.user_id, epd, color),
        )
        self.con.commit()
        return cur.rowcount > 0

    def all(self) -> dict[tuple[str, str], Mark]:
        """Every decision, keyed by the position and side it applies to."""
        rows = self.con.execute(
            "SELECT epd, color, uci, san, decision, note FROM repertoire_marks WHERE user_id = ?",
            (self.user_id,),
        ).fetchall()
        return {
            (r["epd"], r["color"]): Mark(
                epd=r["epd"], color=r["color"], uci=r["uci"], san=r["san"],
                decision=r["decision"], note=r["note"],
            )
            for r in rows
        }

    def listing(self) -> list[dict]:
        """The decisions in a shape the dashboard can render."""
        rows = self.con.execute(
            "SELECT epd, color, uci, san, decision, note, created_at FROM repertoire_marks "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (self.user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.con.close()


def load_marks(path: str = DEFAULT_STATE) -> dict[tuple[str, str], Mark]:
    """Every decision on file, or nothing at all if the player has made none."""
    try:
        store = MarkStore(path)
    except sqlite3.DatabaseError:
        return {}
    try:
        return store.all()
    finally:
        store.close()


def summarise_marks(marks: Iterable[Mark]) -> dict[str, int]:
    counts = {"committed": 0, "ignored": 0}
    for mark in marks:
        if mark.decision in counts:
            counts[mark.decision] += 1
    return counts


class GapStore:
    """What the player has decided about the replies they are not ready for.

    Three states, and they are not the same shape as a mark. "Ignored" removes the gap
    from the list for good — someone who does not play into a line does not need to be
    told about it every month. "Learning" and "practising" are the opposite: they keep the
    gap visible and say what stage it is at, so the section reads as a queue being worked
    through rather than a list of accusations that never shrinks.
    """

    def __init__(self, path: str = DEFAULT_STATE, user_id: str = "local"):
        self.path = path
        self.user_id = user_id
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(GAP_SCHEMA)

    def set(self, epd: str, color: str, decision: str, reply: str = "", line: str = "",
            opening: str = "") -> dict:
        if decision not in GAP_DECISIONS:
            raise ValueError(f"decision must be one of {GAP_DECISIONS}, got {decision!r}")
        self.con.execute(
            "INSERT INTO gap_decisions (user_id, epd, color, reply, line, opening, decision) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, epd, color) DO UPDATE SET "
            "  reply = excluded.reply, line = excluded.line, opening = excluded.opening, "
            "  decision = excluded.decision, created_at = datetime('now')",
            (self.user_id, epd, color, reply, line, opening, decision),
        )
        self.con.commit()
        return {"epd": epd, "color": color, "decision": decision, "reply": reply,
                "line": line, "opening": opening}

    def clear(self, epd: str, color: str) -> bool:
        cur = self.con.execute(
            "DELETE FROM gap_decisions WHERE user_id = ? AND epd = ? AND color = ?",
            (self.user_id, epd, color),
        )
        self.con.commit()
        return cur.rowcount > 0

    def all(self) -> dict[tuple[str, str], str]:
        """Decision by (position, colour) — the shape the gap list needs to filter with."""
        rows = self.con.execute(
            "SELECT epd, color, decision FROM gap_decisions WHERE user_id = ?",
            (self.user_id,),
        ).fetchall()
        return {(r["epd"], r["color"]): r["decision"] for r in rows}

    def listing(self) -> list[dict]:
        rows = self.con.execute(
            "SELECT epd, color, reply, line, opening, decision, created_at FROM gap_decisions "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (self.user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.con.close()


def load_gap_decisions(path: str = DEFAULT_STATE) -> dict[tuple[str, str], str]:
    try:
        store = GapStore(path)
    except sqlite3.DatabaseError:
        return {}
    try:
        return store.all()
    finally:
        store.close()


def apply_gap_decisions(
    gaps: list[dict], decisions: dict[tuple[str, str], str]
) -> list[dict]:
    """Drop the ignored ones; label the rest with where the player has got to.

    Filtering happens here rather than in the walk because the walk should keep producing
    the honest ranking — a decision is a view over it, not a change to the analysis.
    """
    out = []
    for gap in gaps:
        key = (" ".join(str(gap.get("fen", "")).split()[:4]), gap.get("player_color", ""))
        decision = decisions.get(key)
        if decision == "ignored":
            continue
        out.append({**gap, "decision": decision or ""})
    return out
