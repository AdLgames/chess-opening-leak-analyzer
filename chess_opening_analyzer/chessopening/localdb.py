"""Offline opening database: SQLite move statistics + ECO naming, same API as the Explorer.

Build one with `python tools/build_local_db.py` (Lichess monthly PGN dump or your own corpus).
Schema
    meta(key TEXT PRIMARY KEY, value TEXT)
    moves(pos TEXT, uci TEXT, band TEXT, san TEXT, white INT, draws INT, black INT,
          rating_sum INT, PRIMARY KEY (pos, uci, band))
    openings(pos TEXT PRIMARY KEY, eco TEXT, name TEXT)
`pos` is the board EPD (FEN without move counters), so transpositions merge automatically.
"""
from __future__ import annotations

import os
import sqlite3

import chess

from .bands import ALL, neighbours
from .explorer import MoveStats, PositionStats, EMPTY

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS moves (
    pos TEXT NOT NULL, uci TEXT NOT NULL, band TEXT NOT NULL DEFAULT 'all',
    san TEXT NOT NULL,
    white INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black INTEGER DEFAULT 0,
    rating_sum INTEGER DEFAULT 0,
    PRIMARY KEY (pos, uci, band)
);
CREATE TABLE IF NOT EXISTS openings (pos TEXT PRIMARY KEY, eco TEXT, name TEXT);
"""

# The bundled book, unless the player points somewhere else. The override exists because
# the shipped file is a Git LFS pointer until it is pulled, and because a book built from
# a different corpus (a rating band, a time control) should not mean editing the package.
BUNDLED_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "openings.sqlite")
DEFAULT_DB = os.environ.get("LEAKLAB_BOOK") or BUNDLED_DB


def _avg_rating(row: sqlite3.Row) -> int | None:
    """Mean rating behind a move, when the book recorded one."""
    games = row["white"] + row["draws"] + row["black"]
    total = row["rating_sum"] if "rating_sum" in row.keys() else 0
    return round(total / games) if games and total else None


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
        # Books built before rating bands existed have no `band` column, and there are
        # plenty of them — the shipped one included. Detecting it is one query at startup
        # and means an old book keeps working with no migration and no rebuild.
        columns = {r["name"] for r in self.con.execute("PRAGMA table_info(moves)")}
        # Two different questions. The column may be absent entirely (a book built before
        # bands existed — the shipped one included), in which case the query itself has to
        # change; or present but holding only "all" rows, in which case the query is fine
        # and there is simply nothing to choose between. The book is never altered to add
        # the column: it is the player's file, and opening it should not rewrite it.
        self._banded_schema = "band" in columns
        self.has_bands = self._banded_schema and bool(
            self.con.execute("SELECT 1 FROM moves WHERE band != ? LIMIT 1", (ALL,)).fetchone()
        )

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
    def lookup(self, play_uci_csv: str, band: str = ALL, min_band_games: int = 200) -> PositionStats:
        return self.lookup_epd(epd_after(play_uci_csv), band=band, min_band_games=min_band_games)

    def lookup_epd(self, pos: str, band: str = ALL, min_band_games: int = 200) -> PositionStats:
        """Same as `lookup`, for a board EPD you already have.

        `band` asks to be compared against players of a similar strength. If that band is
        too thin here — under `min_band_games` — the comparison widens outward to the
        neighbouring bands and finally to everyone, because a comparison against the right
        population with eight games behind it is worse than one against a slightly wrong
        population with eight hundred. `PositionStats.band` records which was actually used
        so the interface can say so rather than implying a precision it does not have.
        """
        pos = pos.split(" 0 1")[0].strip()
        if not self._banded_schema:
            rows = self.con.execute(
                "SELECT uci, san, white, draws, black, rating_sum FROM moves WHERE pos = ? "
                "ORDER BY (white + draws + black) DESC LIMIT 40",
                (pos,),
            ).fetchall()
            used = ALL
        else:
            wanted = band if self.has_bands else ALL
            rows, used = [], ALL
            for candidate in neighbours(wanted):
                rows = self.con.execute(
                    "SELECT uci, san, white, draws, black, rating_sum FROM moves "
                    "WHERE pos = ? AND band = ? ORDER BY (white + draws + black) DESC LIMIT 40",
                    (pos, candidate),
                ).fetchall()
                total = sum(r["white"] + r["draws"] + r["black"] for r in rows)
                used = candidate
                if rows and (candidate == ALL or total >= min_band_games):
                    break
        if not rows:
            self.stats["db_misses"] += 1
            return EMPTY
        moves = [
            MoveStats(uci=r["uci"], san=r["san"], white=r["white"], draws=r["draws"],
                      black=r["black"], average_rating=_avg_rating(r))
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
            band=used,
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
