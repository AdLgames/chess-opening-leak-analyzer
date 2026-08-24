"""Interactive board support: legal moves, book statistics and on-demand engine lines.

The dashboard's board, drills and openings library all talk to this module, so move
legality and opening statistics are decided by python-chess and the local SQLite book
rather than duplicated in the browser.
"""
from __future__ import annotations

import threading
from typing import Any, Iterable

import chess

from .engine import MATE_CP, EngineAnalyzer, find_engine
from .localdb import LocalOpeningDatabase

START_FEN = chess.STARTING_FEN
MAX_DEPTH = 20
MAX_MULTIPV = 5


class BoardError(ValueError):
    """A FEN, move list or query the caller should fix."""


# --------------------------------------------------------------------------- board
def board_from(
    fen: str | None = None,
    moves: Iterable[str] | None = None,
    san: Iterable[str] | None = None,
) -> chess.Board:
    """Board for `fen` (default: the initial position) with `san` then `moves` applied.

    `san` exists so a report line ("e4 e5 Nf3") can rebuild the real move history,
    which is what opening naming and move numbering need — a bare FEN has none.
    """
    try:
        board = chess.Board(fen) if fen else chess.Board()
    except ValueError as exc:
        raise BoardError(f"Not a legal FEN: {exc}") from exc
    for token in san or []:
        try:
            board.push_san(token)
        except ValueError as exc:
            raise BoardError(f"{token} is not playable in {board.fen()}") from exc
    for uci in moves or []:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise BoardError(f"{uci} is not a move") from exc
        if move not in board.legal_moves:
            raise BoardError(f"{uci} is not legal in {board.fen()}")
        board.push(move)
    return board


def legal_moves(board: chess.Board) -> list[dict[str, Any]]:
    """Every legal move, with the SAN, the resulting FEN and flags the UI needs."""
    out: list[dict[str, Any]] = []
    for move in board.legal_moves:
        san = board.san(move)
        board.push(move)
        entry = {
            "uci": move.uci(),
            "san": san,
            "from": chess.square_name(move.from_square),
            "to": chess.square_name(move.to_square),
            "promotion": chess.piece_symbol(move.promotion) if move.promotion else None,
            "fen_after": board.fen(),
            "check": board.is_check(),
            "mate": board.is_checkmate(),
        }
        board.pop()
        entry["capture"] = board.is_capture(move)
        out.append(entry)
    out.sort(key=lambda m: m["san"])
    return out


def _score_pct(white: int, draws: int, black: int, white_to_move: bool) -> float | None:
    total = white + draws + black
    if not total:
        return None
    wins = white if white_to_move else black
    return round(100.0 * (wins + draws / 2.0) / total, 1)


def book_stats(db: LocalOpeningDatabase, board: chess.Board) -> dict[str, Any]:
    """Book moves for this exact position, ordered by popularity."""
    stats = db.lookup_epd(board.epd())
    total = stats.white + stats.draws + stats.black
    white_to_move = board.turn == chess.WHITE
    moves = []
    for m in stats.moves:
        games = m.white + m.draws + m.black
        moves.append({
            "uci": m.uci,
            "san": m.san,
            "games": games,
            "white": m.white,
            "draws": m.draws,
            "black": m.black,
            "share": round(100.0 * games / total, 1) if total else 0.0,
            "score": _score_pct(m.white, m.draws, m.black, white_to_move),
        })
    return {
        "total": total,
        "white": stats.white,
        "draws": stats.draws,
        "black": stats.black,
        "score": _score_pct(stats.white, stats.draws, stats.black, white_to_move),
        "moves": moves,
        "eco": stats.eco,
        "name": stats.name,
    }


def position_payload(
    fen: str | None = None,
    moves: Iterable[str] | None = None,
    db: LocalOpeningDatabase | None = None,
    san: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Everything the board needs for one position: legality, naming and book stats."""
    board = board_from(fen, moves, san)
    payload: dict[str, Any] = {
        "fen": board.fen(),
        "epd": board.epd(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "move_number": board.fullmove_number,
        "ply": board.ply(),
        "check": board.is_check(),
        "checkmate": board.is_checkmate(),
        "stalemate": board.is_stalemate(),
        "insufficient_material": board.is_insufficient_material(),
        "legal": legal_moves(board),
        # always present so the browser can read one shape whether or not a book is installed
        "book": None,
        "opening": None,
    }
    if db is not None:
        payload["book"] = book_stats(db, board)
        payload["opening"] = name_for(db, board)
    return payload


def name_for(db: LocalOpeningDatabase, board: chess.Board) -> dict[str, str]:
    """The most recent named opening on the way to this position, when the board has history."""
    probe = board.copy()
    while True:
        row = db.opening_name(probe.epd())
        if row:
            return {"eco": row[0], "name": row[1], "at_ply": probe.ply()}
        if not probe.move_stack:
            return {"eco": "", "name": "", "at_ply": 0}
        probe.pop()


# -------------------------------------------------------------------------- engine
_ENGINE_LOCK = threading.Lock()
_SHARED: dict[str, Any] = {"engine": None, "key": None}


def _shared_engine(path: str, depth: int, multipv: int, cache_path: str | None) -> EngineAnalyzer:
    """One long-lived Stockfish process per settings combination.

    Board panes ask for evals interactively, so paying the process start-up on every
    click is noticeable. The engine is kept open and reused under `_ENGINE_LOCK`.
    """
    key = f"{path}|{depth}|{multipv}|{cache_path}"
    current = _SHARED["engine"]
    if current is not None and _SHARED["key"] == key:
        return current
    if current is not None:
        try:
            current.__exit__()
        except Exception:  # noqa: BLE001 - a dead engine is fine to drop
            pass
    engine = EngineAnalyzer(path, depth=depth, multipv=multipv, threads=2,
                            cache_path=cache_path)
    engine.__enter__()
    _SHARED.update(engine=engine, key=key)
    return engine


def close_engine() -> None:
    """Shut the shared engine down (server shutdown, tests)."""
    with _ENGINE_LOCK:
        engine = _SHARED["engine"]
        _SHARED.update(engine=None, key=None)
    if engine is not None:
        try:
            engine.__exit__()
        except Exception:  # noqa: BLE001
            pass


def engine_lines(
    fen: str,
    depth: int = 14,
    multipv: int = 3,
    pv_len: int = 6,
    engine_path: str | None = None,
    cache_path: str | None = None,
) -> dict[str, Any]:
    """Stockfish's top `multipv` continuations for one position, from the mover's side."""
    board = board_from(fen)
    if board.is_game_over():
        return {"fen": board.fen(), "depth": 0, "lines": [], "over": True}
    depth = max(6, min(int(depth), MAX_DEPTH))
    multipv = max(1, min(int(multipv), MAX_MULTIPV))
    path = find_engine(engine_path)
    with _ENGINE_LOCK:
        try:
            eng = _shared_engine(path, depth, multipv, cache_path)
            return eng.evaluate_position(board.fen(), pv_len=pv_len)
        except Exception:  # noqa: BLE001 - engine died mid-session: restart once
            _SHARED.update(engine=None, key=None)
            eng = _shared_engine(path, depth, multipv, cache_path)
            return eng.evaluate_position(board.fen(), pv_len=pv_len)


def cp_text(cp: int | None) -> str:
    """Centipawns as a board-style label, e.g. '+0.42' or 'M4'."""
    if cp is None:
        return "—"
    if abs(cp) >= MATE_CP - 200:
        moves = max(1, (MATE_CP - abs(cp)) // 2 + 1)
        return f"{'M' if cp > 0 else '-M'}{moves}"
    if cp == 0:
        return "0.00"
    return f"{cp / 100.0:+.2f}"
