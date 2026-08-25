"""Precomputed evaluations: ingestion, sign conventions, and serving a verdict.

The dataset's own sign convention is not clearly documented, and getting it backwards would
invert every verdict in the report without anything failing loudly. So the ingest works it
out from the data, and these tests feed it both conventions to prove it does.
"""
from __future__ import annotations

import json
import os
import sys

import chess
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.evalstore import (  # noqa: E402
    EvalStore,
    canonical_epd,
    detect_pov,
    ingest,
    material_balance,
    open_store,
)


def epd_of(*sans: str) -> str:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return board.epd()


def record(epd: str, pvs: list[dict], depth: int = 40, knodes: int = 100000) -> str:
    """One line in the shape the Lichess dataset uses."""
    return json.dumps({"fen": epd, "evals": [{"knodes": knodes, "depth": depth, "pvs": pvs}]})


# ---------------- FEN handling ----------------
def test_a_four_field_fen_becomes_the_epd_the_book_uses():
    board = chess.Board()
    board.push_san("e4")
    assert canonical_epd("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3") == board.epd()


def test_a_full_fen_with_counters_is_accepted_too():
    assert canonical_epd(chess.Board().fen()) == chess.Board().epd()


def test_rubbish_is_rejected_rather_than_crashing():
    assert canonical_epd("not a fen") is None
    assert canonical_epd("") is None


def test_material_balance_is_from_whites_side():
    assert material_balance(chess.Board()) == 0
    # White a queen up
    board = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert material_balance(board) == 900


# ---------------- Sign convention detection ----------------
QUEEN_UP_WHITE = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq -"   # black to move, White +Q
QUEEN_UP_BLACK = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq -"   # black to move, Black +Q


def test_a_white_point_of_view_source_is_recognised():
    """Black to move and a queen down: from White's side that is strongly positive."""
    samples = [(QUEEN_UP_WHITE, 900), (QUEEN_UP_BLACK, -900)]
    pov, white_votes, mover_votes = detect_pov(samples)
    assert pov == "white"
    assert white_votes > mover_votes


def test_a_mover_point_of_view_source_is_recognised():
    """The same two positions, scored for whoever is to move — signs flip."""
    samples = [(QUEEN_UP_WHITE, -900), (QUEEN_UP_BLACK, 900)]
    pov, white_votes, mover_votes = detect_pov(samples)
    assert pov == "mover"
    assert mover_votes > white_votes


def test_level_positions_do_not_get_a_vote():
    """Openings are materially level almost everywhere, which is exactly where the two
    conventions agree — so those positions must not sway the decision."""
    _, white_votes, mover_votes = detect_pov([(epd_of("e4"), 20), (epd_of("e4", "e5"), -15)])
    assert white_votes == 0 and mover_votes == 0


# ---------------- Ingest ----------------
def _italian_lines() -> tuple[str, str, str]:
    """The Italian after 3.Bc4, the position after 4.Nxe5, and 4.Nxe5 in UCI."""
    before = epd_of("e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5")
    after = epd_of("e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "Nxe5")
    return before, after, "f3e5"


def test_only_positions_in_the_book_are_kept(tmp_path):
    """What makes a very large public dataset into a file worth shipping."""
    before, after, _ = _italian_lines()
    lines = [
        record(before, [{"cp": 20, "line": "e1g1 g8f6"}]),
        record(epd_of("d4", "d5", "c4"), [{"cp": 15, "line": "e7e6"}]),  # not in the book
    ]
    out = str(tmp_path / "evals.sqlite")
    stats = ingest(iter(lines), out, wanted={before}, log=lambda *a: None)
    assert stats["kept"] == 1
    assert stats["seen"] == 2

    store = EvalStore(out)
    assert store.get(chess.Board(before + " 0 1")) is not None
    assert store.get(chess.Board(epd_of("d4", "d5", "c4") + " 0 1")) is None


def test_the_deepest_evaluation_wins(tmp_path):
    before, _, _ = _italian_lines()
    line = json.dumps({"fen": before, "evals": [
        {"knodes": 10, "depth": 12, "pvs": [{"cp": 500, "line": "e1g1"}]},
        {"knodes": 900, "depth": 44, "pvs": [{"cp": 20, "line": "e1g1"}]},
    ]})
    out = str(tmp_path / "evals.sqlite")
    ingest(iter([line]), out, wanted={before}, log=lambda *a: None)
    stored = EvalStore(out).get(chess.Board(before + " 0 1"))
    assert stored.depth == 44
    assert stored.best_cp == 20


def test_mate_scores_survive_as_a_large_centipawn_value(tmp_path):
    before, _, _ = _italian_lines()
    out = str(tmp_path / "evals.sqlite")
    ingest(iter([record(before, [{"mate": 3, "line": "e1g1"}])]), out, wanted={before},
           pov="mover", log=lambda *a: None)
    assert EvalStore(out).get(chess.Board(before + " 0 1")).best_cp >= 10000


def test_a_white_point_of_view_file_is_flipped_into_mover_terms(tmp_path):
    """A black-to-move position scored +300 for White must come back as -300 for Black,
    or every verdict about Black's moves would be upside down."""
    black_to_move = epd_of("e4")
    lines = [
        record(QUEEN_UP_WHITE, [{"cp": 900, "line": "e7e5"}]),   # teaches the detector
        record(QUEEN_UP_BLACK, [{"cp": -900, "line": "e7e5"}]),
        record(black_to_move, [{"cp": 300, "line": "e7e5"}]),
    ]
    out = str(tmp_path / "evals.sqlite")
    stats = ingest(iter(lines), out, wanted=None, pov="auto", log=lambda *a: None)
    assert stats["source_pov"] == "white"
    stored = EvalStore(out).get(chess.Board(black_to_move + " 0 1"))
    assert stored.best_cp == -300, "Black is to move and is worse, so it reads negative"


def test_a_mover_point_of_view_file_is_left_alone(tmp_path):
    black_to_move = epd_of("e4")
    lines = [
        record(QUEEN_UP_WHITE, [{"cp": -900, "line": "e7e5"}]),
        record(QUEEN_UP_BLACK, [{"cp": 900, "line": "e7e5"}]),
        record(black_to_move, [{"cp": -300, "line": "e7e5"}]),
    ]
    out = str(tmp_path / "evals.sqlite")
    stats = ingest(iter(lines), out, wanted=None, pov="auto", log=lambda *a: None)
    assert stats["source_pov"] == "mover"
    assert EvalStore(out).get(chess.Board(black_to_move + " 0 1")).best_cp == -300


def test_malformed_lines_are_skipped_not_fatal(tmp_path):
    before, _, _ = _italian_lines()
    lines = ["", "{not json", json.dumps({"fen": before}), record(before, [{"cp": 20, "line": "e1g1"}])]
    out = str(tmp_path / "evals.sqlite")
    stats = ingest(iter(lines), out, wanted={before}, pov="mover", log=lambda *a: None)
    assert stats["kept"] == 1
    assert stats["skipped"] >= 2


# ---------------- Serving a verdict ----------------
def _store_with_italian(tmp_path) -> EvalStore:
    """3.Bc4 Bc5, where castling is best and 4.Nxe5 drops a piece."""
    before, after, _ = _italian_lines()
    lines = [
        record(before, [
            {"cp": 30, "line": "e1g1 g8f6"},
            {"cp": 25, "line": "c2c3 g8f6"},
            {"cp": -270, "line": "f3e5 c6e5"},
        ], depth=40),
        # after 4.Nxe5 it is Black to move, and Black is much better
        record(after, [{"cp": 280, "line": "c6e5"}], depth=38),
    ]
    out = str(tmp_path / "evals.sqlite")
    ingest(iter(lines), out, wanted=None, pov="mover", log=lambda *a: None)
    return EvalStore(out)


def test_a_verdict_is_assembled_without_touching_the_engine(tmp_path):
    store = _store_with_italian(tmp_path)
    before, _, played = _italian_lines()
    fen = chess.Board(before + " 0 1").fen()

    ev = store.evaluate_move(fen, played)
    assert ev is not None
    assert ev.played_san == "Nxe5"
    assert ev.mover == "white"
    assert ev.best_cp == 30
    # The move's own score is the child position read from the other side: Black is +280
    # there, so White is -280.
    assert ev.played_cp == -280
    assert ev.eval_drop_cp == 310
    assert ev.eval_drop_pawns == 3.1
    assert ev.played_rank == 3
    assert [a.san for a in ev.alternatives] == ["O-O", "c3", "Nxe5"]
    assert ev.depth == 40


def test_the_best_move_needs_no_second_lookup(tmp_path):
    store = _store_with_italian(tmp_path)
    before, _, _ = _italian_lines()
    ev = store.evaluate_move(chess.Board(before + " 0 1").fen(), "e1g1")
    assert ev.played_rank == 1
    assert ev.eval_drop_cp == 0


def test_a_missing_position_falls_through_to_the_engine(tmp_path):
    store = _store_with_italian(tmp_path)
    assert store.evaluate_move(chess.Board().fen(), "e2e4") is None


def test_a_missing_child_position_falls_through_too(tmp_path):
    """Without the position after the move there is no honest way to score it."""
    before, _, _ = _italian_lines()
    out = str(tmp_path / "evals.sqlite")
    ingest(iter([record(before, [{"cp": 30, "line": "e1g1 g8f6"}])]), out, wanted=None,
           pov="mover", log=lambda *a: None)
    store = EvalStore(out)
    assert store.evaluate_move(chess.Board(before + " 0 1").fen(), "f3e5") is None


def test_hits_and_misses_are_counted(tmp_path):
    store = _store_with_italian(tmp_path)
    before, _, _ = _italian_lines()
    store.get(chess.Board(before + " 0 1"))
    store.get(chess.Board())
    assert store.hits == 1 and store.misses == 1


def test_no_store_is_not_an_error(tmp_path):
    """The store is an optional accelerator; everything works without it."""
    assert open_store(str(tmp_path / "nothing-here.sqlite")) is None


def test_an_illegal_played_move_is_refused(tmp_path):
    store = _store_with_italian(tmp_path)
    before, _, _ = _italian_lines()
    assert store.evaluate_move(chess.Board(before + " 0 1").fen(), "a1a8") is None
