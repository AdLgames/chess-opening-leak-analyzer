"""Collapsing flagged decisions into one entry per line.

One bad move drags the rest of its line down, so the same repertoire hole reappears as
separate rows further along. These tests pin the rule that decides what is a cause and what
is a consequence.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.summary import group_by_line  # noqa: E402


def row(line: str, ply: int, *, color: str = "white", lost: float = 1.0,
        priority: float = 1.0, move: str = "??", opening: str = "Italian Game") -> dict:
    return {
        "variation_line": line,
        "ply": str(ply),
        "player_color": color,
        "your_move": move,
        "opening": opening,
        "eco": "C50",
        "lost_points": str(lost),
        "lost_points_conservative": str(lost / 2),
        "priority": str(priority),
        "explanation": f"You played {move}.",
    }


def test_a_downstream_leak_nests_under_the_move_that_caused_it():
    rows = [
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5", 7, move="Nxe5"),
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5 Nxe5 d4", 9, move="d4"),
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5 Nxe5 d4 Qh4 g3", 11, move="g3"),
    ]
    groups = group_by_line(rows)
    assert len(groups) == 1, "one hole, not three"
    assert groups[0]["headline"]["your_move"] == "Nxe5", "the earliest mistake leads"
    assert groups[0]["followers"] == 2


def test_the_group_carries_the_whole_branch_cost():
    """Fixing the headline makes the rest moot, so the branch total is what the player
    stands to recover — that is what the ordering should be based on."""
    rows = [
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5", 7, lost=1.0, priority=1.0),
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5 Nxe5 d4", 9, lost=2.0, priority=2.0),
    ]
    group = group_by_line(rows)[0]
    assert group["lost_points"] == 3.0
    assert group["lost_points_conservative"] == 1.5
    assert group["priority"] == 3.0


def test_separate_lines_stay_separate():
    rows = [
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5", 7, move="Nxe5"),
        row("d4 d5 c4 e6 Nc3 Nf6 Bg5 h6 Bxf6", 9, move="Bxf6"),
    ]
    groups = group_by_line(rows)
    assert len(groups) == 2


def test_a_shared_opening_prefix_is_not_a_cause():
    """Both lines start 1.e4 e5 2.Nf3 Nc6, but neither line contains the other's mistake,
    so neither explains the other."""
    rows = [
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5", 7, move="Nxe5"),
        row("e4 e5 Nf3 Nc6 Bb5 a6 Bxc6", 7, move="Bxc6"),
    ]
    assert len(group_by_line(rows)) == 2


def test_the_two_colours_never_nest_into_each_other():
    """The player cannot be both sides of one game, so a White row is never the cause of
    a Black one even when the moves line up."""
    rows = [
        row("e4 e5 Nf3", 3, color="white", move="Nf3"),
        row("e4 e5 Nf3 Nc6 Bc4 Bc5", 6, color="black", move="Bc5"),
    ]
    assert len(group_by_line(rows)) == 2


def test_groups_are_ordered_by_what_is_at_stake():
    rows = [
        row("d4 d5 c4 e6 Nc3", 5, move="Nc3", priority=1.0),
        row("e4 c5 Nf3 d6 Bb5", 5, move="Bb5", priority=4.0),
    ]
    groups = group_by_line(rows)
    assert [g["headline"]["your_move"] for g in groups] == ["Bb5", "Nc3"]


def test_the_deepest_of_several_candidate_parents_does_not_steal_the_branch():
    """Rows arrive out of order; the earliest divergence must still lead, and everything
    below it must land in that one group rather than forming a second root."""
    rows = [
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5 Nxe5 d4", 9, move="d4"),
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5", 7, move="Nxe5"),
        row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5 Nxe5 d4 Qh4 g3 Qxe4", 13, move="Qxe4"),
    ]
    groups = group_by_line(rows)
    assert len(groups) == 1
    assert groups[0]["headline"]["your_move"] == "Nxe5"
    assert {r["your_move"] for r in groups[0]["downstream"]} == {"d4", "Qxe4"}


def test_no_rows_means_no_groups():
    assert group_by_line([]) == []


def test_a_group_shows_both_halves_of_why_it_ranks():
    """A single cost number cannot say whether a line is expensive because it happens
    often or because it is disastrous. The group carries both."""
    rows = [
        dict(row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5", 7, lost=6.0), your_games="20"),
        dict(row("e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5 Nxe5 d4", 9, lost=2.0), your_games="10"),
    ]
    group = group_by_line(rows)[0]
    assert group["games"] == 30
    assert group["cost_per_game"] == round(8.0 / 30, 2)


def test_cost_per_game_survives_a_group_with_no_recorded_games():
    rows = [dict(row("e4 e5", 2), your_games="")]
    assert group_by_line(rows)[0]["cost_per_game"] == 0.0
