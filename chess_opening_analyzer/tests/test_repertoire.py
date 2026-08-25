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
from chessopening.marks import Mark  # noqa: E402
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


# ---------------- Drawing the repertoire ----------------
from chessopening.repertoire import build_tree, tree_totals  # noqa: E402


def line_node(line_uci: str, san: str, color: str = "white", games: int = 10,
              wins: int | None = None, opening: str = "") -> Node:
    """A decision at the end of `line_uci`, carrying its own record."""
    board = chess.Board()
    for uci in filter(None, line_uci.split(",")):
        board.push_uci(uci)
    move = board.parse_san(san)
    wins = games if wins is None else wins
    return Node(
        epd=board.epd(), fen=board.fen(), played_uci=move.uci(), played_san=san,
        player_color=color, ply=len(board.move_stack) + 1,
        move_number=board.fullmove_number, line_san="",
        line_uci=",".join(filter(None, [*line_uci.split(","), move.uci()])),
        opening=opening, wins=wins, draws=0, losses=games - wins,
    )


def test_shared_moves_become_one_trunk_rather_than_two_lines():
    """1.e4 e5 2.Nf3 and 1.e4 e5 2.Bc4 are one opening move, then a fork."""
    nodes = as_nodes(
        line_node("", "e4", games=30),
        line_node("e2e4,e7e5", "Nf3", games=20),
        line_node("e2e4,e7e5", "Bc4", games=10),
    )
    tree = build_tree(nodes, "white")
    assert [t["san"] for t in tree] == ["e4"]
    after_e5 = tree[0]["children"][0]
    assert after_e5["san"] == "e5", "the opponent's move is an edge, not a gap in the tree"
    assert [c["san"] for c in after_e5["children"]] == ["Nf3", "Bc4"], "most played first"


def test_only_the_players_own_moves_carry_a_record():
    nodes = as_nodes(line_node("", "e4", games=30, wins=18))
    tree = build_tree(nodes, "white")
    assert tree[0]["ours"] is True
    assert tree[0]["games"] == 30
    assert tree[0]["score_pct"] == 60.0


def test_an_opponent_edge_carries_the_weight_of_what_is_below_it():
    """So the trunk reads as the trunk, not as whichever leaf happens to be biggest."""
    nodes = as_nodes(
        line_node("", "e4", games=30),
        line_node("e2e4,e7e5", "Nf3", games=20),
        line_node("e2e4,e7e5", "Bc4", games=10),
    )
    after_e5 = build_tree(nodes, "white")[0]["children"][0]
    assert after_e5["ours"] is False
    assert after_e5["games"] == 30


def test_a_good_line_reads_as_strong_and_a_flagged_one_as_weak():
    nodes = as_nodes(
        line_node("", "e4", games=20, wins=13),                  # 65%
        line_node("e2e4,e7e5", "Nf3", games=10, wins=2),         # flagged below
    )
    nf3 = next(n for n in nodes.values() if n.played_san == "Nf3")
    tree = build_tree(nodes, "white", leak_keys={(nf3.epd, nf3.played_uci)})
    assert tree[0]["status"] == "strong"
    assert tree[0]["children"][0]["children"][0]["status"] == "weak"


def test_a_committed_choice_is_never_shown_as_weak():
    """Saying "weak" over the top of a decision is exactly the arguing-back the marks
    exist to stop."""
    nodes = as_nodes(line_node("", "e4", games=20, wins=2))
    e4 = next(iter(nodes.values()))
    mark = Mark(epd=e4.epd, color="white", uci=e4.played_uci, san="e4", decision="committed")
    tree = build_tree(nodes, "white",
                      leak_keys={(e4.epd, e4.played_uci)},
                      marks={(e4.epd, "white"): mark})
    assert tree[0]["status"] == "committed"


def test_a_thin_line_is_left_out_of_the_picture():
    nodes = as_nodes(line_node("", "e4", games=1))
    assert build_tree(nodes, "white", min_games=2) == []


def test_the_tree_stops_at_the_depth_it_is_given():
    nodes = as_nodes(line_node("e2e4,e7e5,g1f3,b8c6", "Bc4", games=10))
    shallow = build_tree(nodes, "white", max_plies=2)
    assert [t["san"] for t in shallow] == ["e4"]
    assert shallow[0]["children"][0]["children"] == []


def test_a_gap_lands_on_the_move_that_leads_to_it_not_a_shallower_one():
    """A gap hangs off the player's move that reaches the position, so it must count
    against 2.d4 rather than against 1.e4 further up the same line."""
    nodes = as_nodes(line_node("", "e4", games=30), line_node("e2e4,c7c6", "d4", games=20))
    for n in nodes.values():
        n.line_san = "e4" if n.played_san == "e4" else "e4 c6 d4"
    gaps = [{"player_color": "white", "line": "1.e4 c6 2.d4 d5"}]
    tree = build_tree(nodes, "white", gaps=gaps)
    assert tree[0]["gaps"] == 0, "1.e4 is not where this gap appears"
    d4 = tree[0]["children"][0]["children"][0]
    assert d4["san"] == "d4"
    assert d4["gaps"] == 1


def test_the_other_colour_is_a_separate_tree():
    nodes = as_nodes(
        line_node("", "e4", color="white", games=10),
        line_node("e2e4", "c6", color="black", games=10),
    )
    assert [t["san"] for t in build_tree(nodes, "white")] == ["e4"]
    assert [t["san"] for t in build_tree(nodes, "black")] == ["e4"], "the opponent's move first"
    assert build_tree(nodes, "black")[0]["children"][0]["san"] == "c6"


def test_totals_count_each_state_across_the_whole_tree():
    nodes = as_nodes(
        line_node("", "e4", games=20, wins=13),
        line_node("e2e4,e7e5", "Nf3", games=10, wins=1),
    )
    nf3 = next(n for n in nodes.values() if n.played_san == "Nf3")
    tree = build_tree(nodes, "white", leak_keys={(nf3.epd, nf3.played_uci)})
    totals = tree_totals(tree)
    assert totals["strong"] == 1
    assert totals["weak"] == 1


def test_an_empty_repertoire_draws_nothing():
    assert build_tree({}, "white") == []
    assert tree_totals([]) == {"strong": 0, "weak": 0, "committed": 0, "played": 0, "gaps": 0}


def test_a_gap_attaches_to_the_line_it_hangs_off_despite_move_numbers():
    """A gap's line is written `1.e4 c6 2.Nc3` while a node's is `e4 c6`; matching them
    naively finds nothing at all, which is how this went unnoticed until the tree said
    every repertoire had zero gaps."""
    nodes = as_nodes(line_node("", "e4", games=30))
    node = next(iter(nodes.values()))
    node.line_san = "e4"
    gaps = [
        {"player_color": "white", "line": "1.e4 c6"},
        {"player_color": "white", "line": "1.e4 e6"},
        {"player_color": "white", "line": "1.d4 d5 2.c4"},   # a different line
        {"player_color": "black", "line": "1.e4 c6"},        # the other colour
    ]
    assert build_tree(nodes, "white", gaps=gaps)[0]["gaps"] == 2
