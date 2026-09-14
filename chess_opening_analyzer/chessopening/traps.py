"""Known opening traps, and which of them the player actually walks into.

The catalogue lives in `data/traps.json`: each entry is the move sequence that
sets the trap, the side that has to find the answer, and the natural-looking
move that loses. Scanning a player's games for them answers a question the
statistics cannot — "what keeps catching me" — with a named line rather than a
number.

Matching is prefix-only: a game counts as having reached a trap when its opening
moves are exactly the trap's line so far. A transposition into the same position
by another move order is not detected, which keeps the claim honest: everything
reported here really was played move for move.

No python-chess here on purpose — this is string work over SAN the loader has
already produced, so it stays cheap and easy to test.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

DEFAULT_TRAPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "traps.json")


def _norm(san: str) -> str:
    """SAN without the decoration: check, mate and annotation marks."""
    return san.rstrip("+#!?").replace("0-0-0", "O-O-O").replace("0-0", "O-O")


@dataclass
class Trap:
    key: str
    name: str
    eco: str
    opening: str
    line: tuple[str, ...]          # SAN plies that set the trap
    victim: str                    # the side to move once the line is on the board
    losing: tuple[str, ...]        # replies that walk into it
    instead: str                   # the reply that does not
    refutation: str                # what the other side plays to punish it
    note: str

    @property
    def move_number(self) -> int:
        """The move number the victim has to get right."""
        return len(self.line) // 2 + 1

    def verdict(self, reply: str | None) -> str:
        """'fell' | 'held' | 'unplayed' for the victim's reply to this line."""
        if reply is None:
            return "unplayed"
        return "fell" if _norm(reply) in {_norm(m) for m in self.losing} else "held"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "name": self.name, "eco": self.eco, "opening": self.opening,
            "line": " ".join(self.line), "victim": self.victim, "losing": list(self.losing),
            "instead": self.instead, "refutation": self.refutation, "note": self.note,
            "move_number": self.move_number,
        }


def load_traps(path: str = DEFAULT_TRAPS) -> list[Trap]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    traps = []
    for entry in raw.get("traps", []):
        line = tuple(entry["line"].split())
        victim = "white" if len(line) % 2 == 0 else "black"
        if victim != entry.get("victim", victim):
            raise ValueError(f"{entry['key']}: line has {len(line)} plies, so the victim is {victim}")
        traps.append(Trap(
            key=entry["key"], name=entry["name"], eco=entry.get("eco", ""),
            opening=entry.get("opening", ""), line=line, victim=victim,
            losing=tuple(entry["losing"]), instead=entry["instead"],
            refutation=entry.get("refutation", ""), note=entry.get("note", ""),
        ))
    return traps


@dataclass
class TrapRecord:
    """One trap, and what happened when this player met it."""

    trap: Trap
    met: int = 0
    fell: int = 0
    held: int = 0
    games: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {**self.trap.to_dict(), "met": self.met, "fell": self.fell, "held": self.held,
                "games": self.games[:6]}


def _reply_to(line: Sequence[str], trap: Trap) -> str | None:
    """The victim's reply to `trap` in this game, or None if they never faced it.

    A game that stops on the trap line itself (the opening phase ran out, or the
    game ended there) did not put the question, so it does not count as met.
    """
    if len(line) <= len(trap.line):
        return None
    for played, expected in zip(line, trap.line):
        if _norm(played) != _norm(expected):
            return None
    return line[len(trap.line)]


def scan_games(games: Iterable[Any], traps: Sequence[Trap] | None = None) -> dict[str, Any]:
    """Which traps this player met, and how often they walked in.

    `games` are GameSummary-shaped: `line_san` (the opening phase, both sides),
    `player_color` and `game_id`. Only traps aimed at the player's side count —
    the question is what catches *them*.
    """
    traps = list(traps if traps is not None else load_traps())
    records: dict[str, TrapRecord] = {}
    for game in games:
        line = str(getattr(game, "line_san", "") or "").split()
        if not line:
            continue
        colour = getattr(game, "player_color", "")
        for trap in traps:
            if trap.victim != colour:
                continue
            reply = _reply_to(line, trap)
            if reply is None:
                continue                       # the line was never on the board
            record = records.setdefault(trap.key, TrapRecord(trap=trap))
            record.met += 1
            verdict = trap.verdict(reply)
            if verdict == "fell":
                record.fell += 1
                record.games.append(str(getattr(game, "game_id", "")))
            elif verdict == "held":
                record.held += 1
    ranked = sorted(records.values(), key=lambda r: (-r.fell, -r.met, r.trap.name))
    return {
        "catalogue": len(traps),
        "met": sum(r.met for r in ranked),
        "fell": sum(r.fell for r in ranked),
        "traps": [r.to_dict() for r in ranked],
    }
