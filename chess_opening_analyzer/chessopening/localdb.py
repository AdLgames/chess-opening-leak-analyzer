"""Offline opening database: SQLite move statistics + ECO naming, same API as the Explorer.

Build one with `python tools/build_local_db.py` (Lichess monthly PGN dump or your own corpus).
Schema
    meta(key TEXT PRIMARY KEY, value TEXT)
    moves(pos TEXT, uci TEXT, san TEXT, white INT, draws INT, black INT, rating_sum INT,
          PRIMARY KEY (pos, uci))
    openings(pos TEXT PRIMARY KEY, eco TEXT, name TEXT)
`pos` is the board EPD (FEN without move counters), so transpositions merge automatically.
"""
from __future__ import annotations

import os
import sqlite3

import chess

from .explorer import MoveStats, PositionStats, EMPTY

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS moves (
    pos TEXT NOT NULL, uci TEXT NOT NULL, san TEXT NOT NULL,
    white INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black INTEGER DEFAULT 0,
    rating_sum INTEGER DEFAULT 0,
    PRIMARY KEY (pos, uci)
);
CREATE TABLE IF NOT EXISTS openings (pos TEXT PRIMARY KEY, eco TEXT, name TEXT);
"""

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "openings.sqlite")


def epd_after(play_uci_csv: str) -> str:
    """EPD of the position reached by a comma-separated UCI move list."""
    board = chess.Board()
    for uci in filter(None, play_uci_csv.split(",")):
        board.push(chess.Move.from_uci(uci))
    return board.epd()


def connect(path: str, create: bool = False) -> sqlite3.Connection:
    if not create and not os.path.exists(path):
        raise FileNotFoundError(
            f"Local opening database not found at {path}. Build one with:\n"
            "  python tools/build_local_db.py --months 2013-01 --max-moves 15"
        )
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


class LocalOpeningDatabase:
    """Drop-in replacement for OpeningExplorer.lookup() backed by a local SQLite file."""

    def __init__(self, path: str = DEFAULT_DB, min_position_games: int = 0):
        self.path = path
        self.min_position_games = min_position_games
        self.con = connect(path)
        self.con.row_factory = sqlite3.Row
        self.stats = {"cache_hits": 0, "api_calls": 0, "errors": 0, "db_hits": 0, "db_misses": 0}
        self._meta = {r["key"]: r["value"] for r in self.con.execute("SELECT key, value FROM meta")}

    # -------- introspection --------
    @property
    def description(self) -> str:
        src = self._meta.get("source", "unknown corpus")
        games = self._meta.get("games", "?")
        filters = self._meta.get("filters", "")
        return f"local db {os.path.basename(self.path)} ({games} games from {src}; {filters})"

    def total_games(self) -> int:
        return int(self._meta.get("games", 0) or 0)

    # -------- lookup --------
    def lookup(self, play_uci_csv: str) -> PositionStats:
        return self.lookup_epd(epd_after(play_uci_csv))

    def lookup_epd(self, pos: str) -> PositionStats:
        """Same as `lookup`, for a board EPD you already have."""
        pos = pos.split(" 0 1")[0].strip()
        rows = self.con.execute(
            "SELECT uci, san, white, draws, black FROM moves WHERE pos = ? "
            "ORDER BY (white + draws + black) DESC LIMIT 40",
            (pos,),
        ).fetchall()
        if not rows:
            self.stats["db_misses"] += 1
            return EMPTY
        moves = [
            MoveStats(uci=r["uci"], san=r["san"], white=r["white"], draws=r["draws"], black=r["black"])
            for r in rows
        ]
        total_w = sum(m.white for m in moves)
        total_d = sum(m.draws for m in moves)
        total_b = sum(m.black for m in moves)
        if total_w + total_d + total_b < self.min_position_games:
            self.stats["db_misses"] += 1
            return EMPTY
        name_row = self.con.execute("SELECT eco, name FROM openings WHERE pos = ?", (pos,)).fetchone()
        self.stats["db_hits"] += 1
        return PositionStats(
            eco=name_row["eco"] if name_row else "",
            name=name_row["name"] if name_row else "",
            white=total_w,
            draws=total_d,
            black=total_b,
            moves=moves,
        )

    # -------- naming and search --------
    def opening_name(self, pos: str) -> tuple[str, str] | None:
        """(eco, name) for this exact EPD, or None when the book does not name it."""
        row = self.con.execute("SELECT eco, name FROM openings WHERE pos = ?", (pos,)).fetchone()
        return (row["eco"], row["name"]) if row else None

    def search_openings(self, query: str, limit: int = 40) -> list[dict]:
        """Named openings whose name or ECO code matches `query`, most-played first.

        Each hit carries the EPD, so the board can jump straight to that position.
        """
        query = (query or "").strip()
        if not query:
            rows = self.con.execute(
                "SELECT o.eco, o.name, o.pos, "
                "       (SELECT SUM(white + draws + black) FROM moves m WHERE m.pos = o.pos) AS games "
                "FROM openings o ORDER BY games DESC NULLS LAST LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            like = f"%{query}%"
            rows = self.con.execute(
                "SELECT o.eco, o.name, o.pos, "
                "       (SELECT SUM(white + draws + black) FROM moves m WHERE m.pos = o.pos) AS games "
                "FROM openings o WHERE o.name LIKE ? OR o.eco LIKE ? "
                "ORDER BY games DESC NULLS LAST LIMIT ?",
                (like, like, limit),
            ).fetchall()
        return [{"eco": r["eco"], "name": r["name"], "epd": r["pos"],
                 "fen": f"{r['pos']} 0 1", "games": int(r["games"] or 0)} for r in rows]

    def close(self) -> None:
        self.con.close()
