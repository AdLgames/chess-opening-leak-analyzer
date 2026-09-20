"""Precomputed Stockfish evaluations, so the deep calculation costs nothing at run time.

Lichess publishes a CC0 dataset of position evaluations (`lichess_db_eval.jsonl.zst`, see
https://database.lichess.org/). Opening positions are the most heavily analysed positions
in existence, so for a book of opening lines the coverage is close to total, at depths far
beyond anything worth running on demand. Ingesting it turns the engine pass into a lookup.

The store is a separate SQLite file from the opening book: entirely optional, git-ignored,
and everything still works without it — a miss just falls through to the local engine.

## Sign convention

The codebase scores everything from the side to move's point of view (`engine._cp` takes
`score.pov(mover)`), so that is what this store holds. The dataset's own convention is not
clearly documented, and getting it backwards would invert every verdict silently, so
`detect_pov` works it out from the data instead of trusting a guess: in positions with a
lopsided material count, an evaluation from White's point of view tracks White's material,
while one from the mover's point of view tracks the mover's.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Iterator

import chess

from .engine import MATE_CP, Alternative, PositionEval

SCHEMA = """
CREATE TABLE IF NOT EXISTS evals (
    pos TEXT PRIMARY KEY,       -- EPD, canonicalised through python-chess
    depth INTEGER NOT NULL,
    knodes INTEGER NOT NULL,
    pvs TEXT NOT NULL           -- JSON [{"cp"|"mate": int, "line": "uci uci ..."}], mover POV
);
CREATE TABLE IF NOT EXISTS eval_meta (key TEXT PRIMARY KEY, value TEXT);
"""

DEFAULT_EVALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "evals.sqlite")

PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0,
}


def material_balance(board: chess.Board) -> int:
    """Material in centipawns from White's point of view."""
    total = 0
    for piece_type, value in PIECE_VALUES.items():
        total += value * len(board.pieces(piece_type, chess.WHITE))
        total -= value * len(board.pieces(piece_type, chess.BLACK))
    return total


def canonical_epd(fen: str) -> str | None:
    """The dataset's 4-field FEN as the EPD the rest of the app uses, or None if unusable.

    Going through python-chess means the ep-square and castling spellings match the book's
    keys exactly, rather than matching only when the two happen to agree.
    """
    parts = fen.split()
    if len(parts) < 4:
        return None
    try:
        return chess.Board(" ".join(parts[:4]) + " 0 1").epd()
    except ValueError:
        return None


def _score_cp(pv: dict[str, Any]) -> int | None:
    if pv.get("mate") is not None:
        mate = int(pv["mate"])
        return MATE_CP if mate > 0 else -MATE_CP
    if pv.get("cp") is not None:
        return int(pv["cp"])
    return None


def detect_pov(samples: Iterable[tuple[str, int]], min_imbalance: int = 300) -> tuple[str, int, int]:
    """Work out whether the source scores from White's side or the mover's.

    `samples` are `(epd, cp)` pairs straight from the file. Only lopsided positions vote,
    because those are the ones where the two conventions disagree unmistakably. Returns
    `(pov, white_votes, mover_votes)`; the caller decides whether the margin is convincing.
    """
    white_votes = mover_votes = 0
    for epd, cp in samples:
        try:
            board = chess.Board(epd + " 0 1")
        except ValueError:
            continue
        balance = material_balance(board)
        if abs(balance) < min_imbalance or cp == 0:
            continue
        # White's point of view: the sign follows White's material.
        if (cp > 0) == (balance > 0):
            white_votes += 1
        # The mover's: the sign follows the mover's material.
        mover_balance = balance if board.turn == chess.WHITE else -balance
        if (cp > 0) == (mover_balance > 0):
            mover_votes += 1
    return ("white" if white_votes >= mover_votes else "mover"), white_votes, mover_votes


def _to_mover_pov(cp: int, board: chess.Board, source_pov: str) -> int:
    if source_pov == "white" and board.turn == chess.BLACK:
        return -cp
    return cp


def connect(path: str, create: bool = False) -> sqlite3.Connection:
    if not create and not os.path.exists(path):
        raise FileNotFoundError(f"No evaluation store at {path}")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def ingest(
    lines: Iterator[str],
    out_path: str,
    wanted: set[str] | None = None,
    pov: str = "auto",
    max_pvs: int = 3,
    sample_size: int = 4000,
    log=print,
) -> dict[str, Any]:
    """Stream JSON lines into an evaluation store, keeping only positions we care about.

    `wanted` is the set of EPDs in the opening book; everything else is dropped, which is
    what keeps a very large public dataset down to a file worth shipping. Passing None keeps
    everything.
    """
    con = connect(out_path, create=True)
    seen = kept = skipped = 0
    samples: list[tuple[str, int]] = []
    pending: list[tuple[str, int, int, str]] = []
    resolved_pov = None if pov == "auto" else pov

    def flush() -> None:
        con.executemany(
            "INSERT OR REPLACE INTO evals (pos, depth, knodes, pvs) VALUES (?, ?, ?, ?)", pending
        )
        con.commit()
        pending.clear()

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        seen += 1
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            skipped += 1
            continue
        epd = canonical_epd(record.get("fen", ""))
        if epd is None:
            skipped += 1
            continue
        if wanted is not None and epd not in wanted:
            continue

        # Deepest evaluation wins; among equals, the one with the most lines.
        evals = record.get("evals") or []
        best = None
        for ev in evals:
            key = (int(ev.get("depth", 0)), len(ev.get("pvs") or []))
            if best is None or key > best[0]:
                best = (key, ev)
        if best is None:
            skipped += 1
            continue
        (depth, _), chosen = best
        pvs = [pv for pv in (chosen.get("pvs") or []) if _score_cp(pv) is not None][:max_pvs]
        if not pvs:
            skipped += 1
            continue

        if resolved_pov is None:
            samples.append((epd, _score_cp(pvs[0])))
            if len(samples) >= sample_size:
                resolved_pov, white_votes, mover_votes = detect_pov(samples)
                log(f"Evaluation point of view: {resolved_pov} "
                    f"(white {white_votes} / mover {mover_votes} over {len(samples)} samples)")

        pending.append((epd, depth, int(chosen.get("knodes", 0)),
                        json.dumps([{**pv, "cp": _score_cp(pv)} for pv in pvs])))
        kept += 1
        if len(pending) >= 2000:
            flush()

    flush()

    if resolved_pov is None:
        # Too few lopsided positions to be sure: the opening is materially level almost
        # everywhere, which is exactly where the two conventions agree anyway.
        resolved_pov, white_votes, mover_votes = detect_pov(samples)
        log(f"Evaluation point of view: {resolved_pov} (weak sample: "
            f"white {white_votes} / mover {mover_votes} over {len(samples)})")

    # Normalise everything to the mover's point of view now that we know the convention.
    if resolved_pov == "white":
        rows = con.execute("SELECT pos, pvs FROM evals").fetchall()
        fixed = []
        for pos, pvs_json in rows:
            board = chess.Board(pos + " 0 1")
            if board.turn == chess.WHITE:
                continue
            pvs = json.loads(pvs_json)
            for pv in pvs:
                pv["cp"] = -pv["cp"]
                if pv.get("mate") is not None:
                    pv["mate"] = -pv["mate"]
            fixed.append((json.dumps(pvs), pos))
        con.executemany("UPDATE evals SET pvs = ? WHERE pos = ?", fixed)
        con.commit()
        log(f"Flipped {len(fixed)} black-to-move positions into mover point of view")

    con.executemany(
        "INSERT OR REPLACE INTO eval_meta (key, value) VALUES (?, ?)",
        [("positions", str(kept)), ("source_pov", resolved_pov), ("stored_pov", "mover"),
         ("max_pvs", str(max_pvs))],
    )
    con.commit()
    con.close()
    return {"seen": seen, "kept": kept, "skipped": skipped, "source_pov": resolved_pov}


@dataclass
class StoredEval:
    epd: str
    depth: int
    knodes: int
    pvs: list[dict[str, Any]]  # mover point of view

    @property
    def best_cp(self) -> int:
        return int(self.pvs[0]["cp"]) if self.pvs else 0


class EvalStore:
    """Read side of the precomputed evaluations. Missing positions return None."""

    def __init__(self, path: str = DEFAULT_EVALS):
        self.path = path
        self.con = connect(path)
        self.con.row_factory = sqlite3.Row
        self.meta = {r["key"]: r["value"] for r in self.con.execute("SELECT key, value FROM eval_meta")}
        self.hits = 0
        self.misses = 0

    @property
    def positions(self) -> int:
        return int(self.meta.get("positions", 0) or 0)

    def get(self, board: chess.Board) -> StoredEval | None:
        row = self.con.execute(
            "SELECT pos, depth, knodes, pvs FROM evals WHERE pos = ?", (board.epd(),)
        ).fetchone()
        if row is None:
            self.misses += 1
            return None
        self.hits += 1
        return StoredEval(epd=row["pos"], depth=row["depth"], knodes=row["knodes"],
                          pvs=json.loads(row["pvs"]))

    def evaluate_move(self, fen: str, played_uci: str) -> PositionEval | None:
        """The same verdict `EngineAnalyzer.evaluate_move` gives, assembled from the store.

        Needs both the position and the one after the played move: the move's own score is
        the child position's best line seen from the other side, which is why the sign flips.
        Returns None when either is absent, so the caller can fall back to the engine.
        """
        board = chess.Board(fen)
        here = self.get(board)
        if here is None or not here.pvs:
            return None

        alternatives: list[Alternative] = []
        played_rank = None
        for i, pv in enumerate(here.pvs, start=1):
            first = (pv.get("line") or "").split()
            if not first:
                continue
            try:
                move = chess.Move.from_uci(first[0])
                san = board.san(move)
            except (ValueError, AssertionError):
                continue
            alternatives.append(Alternative(san=san, uci=first[0], cp=int(pv["cp"])))
            if first[0] == played_uci and played_rank is None:
                played_rank = i

        if not alternatives:
            return None

        child = board.copy()
        try:
            played_move = chess.Move.from_uci(played_uci)
            played_san = board.san(played_move)
            child.push(played_move)
        except (ValueError, AssertionError):
            return None

        best_cp = alternatives[0].cp
        refutation_uci = refutation_san = ""
        if played_rank == 1:
            played_cp = best_cp
        else:
            after = self.get(child)
            if after is None or not after.pvs:
                return None
            played_cp = -after.best_cp  # the child is scored for the opponent
            # The opponent's best reply is the move the player walked into.
            reply = (after.pvs[0].get("line") or "").split()
            if reply:
                try:
                    reply_move = chess.Move.from_uci(reply[0])
                    refutation_san = child.san(reply_move)
                    refutation_uci = reply[0]
                except (ValueError, AssertionError):
                    pass

        return PositionEval(
            fen=fen,
            played_uci=played_uci,
            played_san=played_san,
            mover="white" if board.turn == chess.WHITE else "black",
            best_cp=best_cp,
            played_cp=played_cp,
            eval_drop_cp=max(0, best_cp - played_cp),
            played_rank=played_rank,
            alternatives=alternatives,
            depth=here.depth,
            refutation_uci=refutation_uci,
            refutation_san=refutation_san,
        )

    def close(self) -> None:
        self.con.close()


def open_store(path: str = DEFAULT_EVALS) -> EvalStore | None:
    """The store if it has been built, otherwise None — it is always optional."""
    try:
        return EvalStore(path)
    except (FileNotFoundError, sqlite3.DatabaseError):
        return None
