"""Tests for the board layer that powers the review, drill and library panes."""

from __future__ import annotations

import pytest

from chessopening.board import (BoardError, board_from, cp_text, legal_moves,
                                position_payload)


def test_board_from_applies_uci_moves() -> None:
    board = board_from(moves=["e2e4", "e7e5"])
    assert board.fullmove_number == 2
    assert board.turn is True  # white to move again


def test_board_from_applies_san_history() -> None:
    board = board_from(san=["e4", "e5", "Nf3"])
    assert [m.uci() for m in board.move_stack] == ["e2e4", "e7e5", "g1f3"]


def test_board_from_rejects_an_illegal_move() -> None:
    with pytest.raises(BoardError):
        board_from(moves=["e2e5"])


def test_board_from_rejects_a_broken_fen() -> None:
    with pytest.raises(BoardError):
        board_from("not a fen")


def test_legal_moves_describe_each_option() -> None:
    moves = legal_moves(board_from(san=["e4", "e5"]))
    by_uci = {m["uci"]: m for m in moves}
    assert by_uci["g1f3"]["san"] == "Nf3"
    assert by_uci["g1f3"]["from"] == "g1"
    assert by_uci["g1f3"]["to"] == "f3"
    assert by_uci["g1f3"]["capture"] is False
    assert by_uci["g1f3"]["fen_after"].startswith("rnbqkbnr/pppp1ppp/8/4p3")


def test_legal_moves_flag_captures_and_promotions() -> None:
    moves = legal_moves(board_from("8/P7/8/8/8/8/8/K6k w - - 0 1"))
    promos = {m["promotion"] for m in moves if m["from"] == "a7"}
    assert promos == {"q", "r", "b", "n"}


def test_position_payload_without_a_database() -> None:
    payload = position_payload(san=["e4", "e5"])
    assert payload["turn"] == "white"
    assert payload["move_number"] == 2
    assert payload["ply"] == 2
    assert payload["book"] is None
    assert len(payload["legal"]) == 29
    assert payload["check"] is False


def test_position_payload_reports_mate() -> None:
    payload = position_payload(san=["f3", "e5", "g4", "Qh4"])
    assert payload["checkmate"] is True
    assert payload["check"] is True
    assert payload["legal"] == []


@pytest.mark.parametrize(
    ("cp", "text"),
    [(0, "0.00"), (80, "+0.80"), (-155, "-1.55"), (None, "—")],
)
def test_cp_text_formats_from_the_mover_point_of_view(cp: int | None, text: str) -> None:
    assert cp_text(cp) == text
