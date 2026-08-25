"""Inferring what the player intends to play, and what they are unprepared for.

The book here is a small hand-built stub rather than the shipped database, so the walk is
tested against known probabilities instead of whatever the 2013 dumps happen to contain.
"""
from __future__ import annotations

import os
import sys

import chess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.analyze import Node  # noqa: E402
from chessopening.explorer import MoveStats, PositionStats  # noqa: E402
from chessopening.repertoire import (  # noqa: E402
    build_repertoire,
    faced_counts,
    find_gaps,
)


def node(line_uci: str, san: str, color: str = "black", games: int = 10) -> Node:
    """A Node for the position reached by `line_uci`, where the player chose `san`."""
    board = chess.Board()
    for uci in filter(None, line_uci.split(",")):
        board.push_uci(uci)
    move = board.parse_san(san)
    return Node(
        epd=board.epd(),
        fen=board.fen(),
        played_uci=move.uci(),
        played_san=san,
        player_color=color,
        ply=len(board.move_stack) + 1,
        move_number=board.fullmove_number,
        line_san="",
        line_uci=line_uci,
        wins=games, draws=0, losses=0,
    )


def as_nodes(*nodes: Node) -> dict:
    return {(n.epd, n.played_uci): n for n in nodes}


def epd_of(*ucis: str) -> str:
    board = chess.Board()
    for uci in ucis:
        board.push_uci(uci)
    return board.epd()


class StubBook:
    """Just the two methods the walk uses, over a dict of EPD -> replies."""

    def __init__(self, replies: dict[str, list[tuple[str, int]]], names: dict | None = None):
        # The walk starts at move one, so White's opening move is an opponent choice like
        # any other. Every stub gets 1.e4 unless it says otherwise.
        self._replies = {epd_of(): [("e4", 100)], **replies}
        self._names = names or {}

    def lookup_epd(self, epd: str) -> PositionStats:
        entries = self._replies.get(epd, [])
        moves = []
        board = chess.Board(epd + " 0 1")
        for san, games in entries:
            move = board.parse_san(san)
            moves.append(MoveStats(uci=move.uci(), san=san, white=games, draws=0, black=0))
        return PositionStats(eco="", name="", white=sum(m.games for m in moves),
                             draws=0, black=0, moves=moves)

    def opening_name(self, epd: str):
        return self._names.get(epd)


# ---------------- Reading intent from past games ----------------
def test_the_most_played_move_is_taken_as_the_intended_one():
    nodes = as_nodes(
        node("e2e4", "c6", games=30),   # the Caro-Kann, most of the time
        node("e2e4", "e5", games=4),    # and occasionally something else
    )
    rep = build_repertoire(nodes, "black")
    intent = rep[epd_of("e2e4")]
    assert intent.san == "c6"
    assert intent.games == 30
    assert round(intent.share, 2) == round(30 / 34, 2), "how settled the choice is"


def test_a_position_seen_once_is_not_yet_an_intention():
    nodes = as_nodes(node("e2e4", "c6", games=1))
    assert build_repertoire(nodes, "black", min_games=2) == {}


def test_the_other_colour_is_ignored():
    nodes = as_nodes(node("", "e4", color="white", games=20))
    assert build_repertoire(nodes, "black") == {}
    assert build_repertoire(nodes, "white")


def test_games_reaching_a_position_are_counted_across_every_move_tried_there():
    nodes = as_nodes(node("e2e4", "c6", games=30), node("e2e4", "e5", games=4))
    assert faced_counts(nodes)[epd_of("e2e4")] == 34


# ---------------- The coverage walk ----------------
def test_a_common_reply_the_player_has_never_met_is_reported():
    """Black always answers 1.e4 with 1...c6. White's book replies 2.d4 (60%) and 2.Nc3
    (40%), and this player has only ever seen 2.d4."""
    nodes = as_nodes(
        node("e2e4", "c6", games=30),
        node("e2e4,c7c6,d2d4", "d5", games=30),
    )
    book = StubBook({epd_of("e2e4", "c7c6"): [("d4", 60), ("Nc3", 40)]})
    gaps = find_gaps(book, nodes, "black", max_plies=6, min_book_games=10)

    assert [g["reply"] for g in gaps] == ["Nc3"]
    gap = gaps[0]
    assert gap["times_faced"] == 0
    assert gap["share_pct"] == 40.0
    assert gap["reach_pct"] == 40.0, "reached whenever White chooses it"
    assert gap["line"] == "1.e4 c6 2.Nc3"


def test_probability_compounds_down_the_branch():
    """Two opponent choices deep, so the second one is only reached part of the time and
    must be ranked accordingly."""
    nodes = as_nodes(
        node("e2e4", "c6", games=30),
        node("e2e4,c7c6,d2d4", "d5", games=30),
    )
    book = StubBook({
        epd_of("e2e4", "c7c6"): [("d4", 50), ("Nc3", 50)],
        epd_of("e2e4", "c7c6", "d2d4", "d7d5"): [("e5", 50), ("Nc3", 50)],
    })
    # Keyed by line, not by move: Nc3 turns up at two different depths here, which is
    # exactly the ambiguity the line label exists to resolve.
    gaps = {g["line"]: g for g in find_gaps(book, nodes, "black", max_plies=8, min_book_games=10)}
    # 2.Nc3 is met half the time; 2.d4 d5 3.e5 only a quarter of the time.
    assert gaps["1.e4 c6 2.Nc3"]["reach_pct"] == 50.0
    assert gaps["1.e4 c6 2.d4 d5 3.e5"]["reach_pct"] == 25.0
    assert gaps["1.e4 c6 2.d4 d5 3.Nc3"]["reach_pct"] == 25.0


def test_a_reply_the_player_knows_well_is_not_a_gap():
    nodes = as_nodes(
        node("e2e4", "c6", games=30),
        node("e2e4,c7c6,d2d4", "d5", games=30),
    )
    book = StubBook({epd_of("e2e4", "c7c6"): [("d4", 100)]})
    assert find_gaps(book, nodes, "black", max_plies=6, min_book_games=10) == []


def test_a_reply_met_only_once_or_twice_still_counts_as_a_gap():
    nodes = as_nodes(
        node("e2e4", "c6", games=30),
        node("e2e4,c7c6,d2d4", "d5", games=28),
        node("e2e4,c7c6,b1c3", "d5", games=2),  # seen twice in thirty games
    )
    book = StubBook({epd_of("e2e4", "c7c6"): [("d4", 60), ("Nc3", 40)]})
    gaps = find_gaps(book, nodes, "black", max_plies=6, min_faced=3, min_book_games=10)
    assert [(g["reply"], g["times_faced"]) for g in gaps] == [("Nc3", 2)]


def test_rare_sidelines_are_not_worth_preparing():
    """A reply played in 1% of games is not what loses a club player rating, and reporting
    it would bury the ones that do."""
    nodes = as_nodes(node("e2e4", "c6", games=30))
    book = StubBook({epd_of("e2e4", "c7c6"): [("d4", 99), ("Na3", 1)]})
    gaps = find_gaps(book, nodes, "black", max_plies=4, min_reach=0.02, min_book_games=10)
    assert [g["reply"] for g in gaps] == ["d4"], "d4 is unfaced and common; Na3 is neither"


def test_a_position_the_book_barely_knows_is_not_used_to_make_claims():
    nodes = as_nodes(node("e2e4", "c6", games=30))
    book = StubBook({epd_of("e2e4", "c7c6"): [("d4", 3)]})
    assert find_gaps(book, nodes, "black", max_plies=4, min_book_games=50) == []


def test_no_games_means_no_repertoire_and_no_claims():
    assert find_gaps(StubBook({}), {}, "black") == []


def test_the_walk_stops_at_the_depth_it_is_given():
    nodes = as_nodes(
        node("e2e4", "c6", games=30),
        node("e2e4,c7c6,d2d4", "d5", games=30),
    )
    book = StubBook({
        epd_of("e2e4", "c7c6"): [("d4", 100)],
        epd_of("e2e4", "c7c6", "d2d4", "d7d5"): [("e5", 100)],
    })
    shallow = find_gaps(book, nodes, "black", max_plies=2, min_book_games=10)
    deep = find_gaps(book, nodes, "black", max_plies=8, min_book_games=10)
    assert shallow == []
    assert [g["reply"] for g in deep] == ["e5"]


def test_the_gap_explains_itself_in_words():
    nodes = as_nodes(
        node("e2e4", "c6", games=30),
        node("e2e4,c7c6,d2d4", "d5", games=30),
    )
    book = StubBook(
        {epd_of("e2e4", "c7c6"): [("d4", 60), ("Nc3", 40)]},
        names={epd_of("e2e4", "c7c6"): ("B10", "Caro-Kann Defence")},
    )
    text = find_gaps(book, nodes, "black", max_plies=6, min_book_games=10)[0]["explanation"]
    assert "Nc3" in text
    assert "Caro-Kann Defence" in text
    assert "40% of games" in text
    assert "never faced it" in text
