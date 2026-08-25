"""Sample-size handling: confidence intervals, shrinkage, and what may be flagged.

Values here are hand-computed rather than captured from a run, so an intentional change to
the statistical model shows up as an intentional change to a test.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.analyze import (  # noqa: E402
    Node,
    confidence_label,
    explain,
    flags_winrate_decline,
)
from chessopening.explorer import (  # noqa: E402
    MoveStats,
    PositionStats,
    score_interval,
    shrink_toward,
)


def _interval(wins: int, draws: int, losses: int, z: float = 0.8416):
    """Interval for a player-perspective record (already win/draw/loss for the player)."""
    return score_interval(wins, draws, losses, "white", z=z)


# ---------------- Interval maths ----------------
def test_empty_record_has_no_interval():
    assert score_interval(0, 0, 0, "white") is None


def test_interval_is_centred_on_the_score_and_respects_colour():
    # 6 wins, 2 draws, 2 losses from White's side -> 0.7; the same record read from Black's
    # side is the mirror, 0.3.
    white_score, lo, hi = score_interval(6, 2, 2, "white")
    assert white_score == pytest.approx(0.7)
    assert lo < 0.7 < hi
    black_score, _, _ = score_interval(6, 2, 2, "black")
    assert black_score == pytest.approx(0.3)


def test_a_drawn_record_is_more_certain_than_a_swingy_one():
    """Both score 50%, but all-draws is genuinely better evidence for 50% than half
    wins and half losses — the trinomial variance is what captures that."""
    _, draw_lo, draw_hi = _interval(0, 20, 0)
    _, swing_lo, swing_hi = _interval(10, 0, 10)
    assert (draw_hi - draw_lo) < (swing_hi - swing_lo)


def test_a_one_sided_record_still_gets_a_usable_interval():
    """Three straight losses have zero sample variance. Without a floor the interval
    would collapse to a point and claim certainty from three games."""
    score, lo, hi = _interval(0, 0, 3)
    assert score == 0.0
    assert hi > 0.1, "a floor must keep the interval open"
    assert lo == 0.0, "clamped at the bottom of the range"


def test_more_games_narrow_the_interval():
    _, few_lo, few_hi = _interval(1, 0, 2)
    _, many_lo, many_hi = _interval(10, 0, 20)
    assert (many_hi - many_lo) < (few_hi - few_lo)


# ---------------- Shrinkage ----------------
def test_a_thin_move_is_pulled_almost_all_the_way_to_the_prior():
    # 2 games at 100% against a position that averages 45%: the move's own record should
    # barely register.
    assert shrink_toward(1.0, 2, 0.45, prior_games=50) == pytest.approx(0.4712, abs=1e-4)


def test_a_well_sampled_move_keeps_its_own_score():
    assert shrink_toward(0.22, 2000, 0.45, prior_games=50) == pytest.approx(0.2256, abs=1e-4)


def test_shrinkage_falls_back_to_the_prior_with_no_games():
    assert shrink_toward(0.9, 0, 0.45) == 0.45


# ---------------- Baseline selection ----------------
def _position() -> PositionStats:
    """A position worth 45% to White, with one well-played move and one barely-played one."""
    return PositionStats(
        eco="C50",
        name="Italian Game",
        white=4000,
        draws=1000,
        black=5000,
        moves=[
            MoveStats(uci="e1g1", san="O-O", white=3000, draws=800, black=2200),
            MoveStats(uci="f3e5", san="Nxe5", white=200, draws=40, black=760),
            MoveStats(uci="h2h4", san="h4", white=2, draws=0, black=0),
        ],
    )


def test_a_barely_played_move_does_not_get_to_set_the_baseline():
    """h4 has two games, both won. Taken at face value it would claim 100% and make any
    player look terrible; the position average is the honest comparison instead."""
    score, source, games = _position().baseline_for("h2h4", "white", min_move_games=30)
    assert source == "position"
    assert score == pytest.approx(0.45)
    assert games == 10000


def test_a_well_played_move_sets_the_baseline_but_is_still_shrunk():
    score, source, games = _position().baseline_for("f3e5", "white", min_move_games=30)
    assert source == "move"
    assert games == 1000
    # 22% over 1000 games, pulled slightly toward the position's 45%
    assert score == pytest.approx(0.2310, abs=1e-4)
    assert 0.22 < score < 0.24


def test_a_move_absent_from_the_book_falls_back_to_the_position():
    _, source, _ = _position().baseline_for("a2a3", "white", min_move_games=30)
    assert source == "position"


# ---------------- The flag rule ----------------
def test_three_games_below_the_book_are_not_flagged():
    """The motivating case: 1 win, 2 losses is 33%, which looks 12 points below a 45%
    book — but three games cannot support that claim."""
    _, _, hi = _interval(1, 0, 2)
    assert not flags_winrate_decline(hi, 0.45, 0.333 - 0.45, 0.06)


def test_the_same_score_over_twenty_games_is_flagged():
    _, _, hi = _interval(6, 1, 13)  # 32.5% over 20 games
    assert flags_winrate_decline(hi, 0.45, 0.325 - 0.45, 0.06)


def test_a_gap_too_small_to_matter_is_not_flagged_however_many_games():
    _, _, hi = _interval(40, 10, 50)  # 45% over 100 games, level with the book
    assert not flags_winrate_decline(hi, 0.46, 0.45 - 0.46, 0.06)


def test_no_baseline_means_no_claim():
    assert not flags_winrate_decline(0.1, None, None, 0.06)


# ---------------- Reader-facing output ----------------
def test_confidence_needs_both_sides_to_be_well_sampled():
    assert confidence_label(20, 800, "move") == "high"
    assert confidence_label(4, 800, "move") == "low", "few games of the player's own"
    assert confidence_label(20, 40, "move") == "low", "the book barely knows the position"
    assert confidence_label(9, 1000, "move") == "medium"


def _node(**kw) -> Node:
    base = dict(
        epd="", fen="", played_uci="f3e5", played_san="Nxe5", player_color="white",
        ply=7, move_number=4, line_san="", line_uci="", wins=1, draws=0, losses=8,
    )
    base.update(kw)
    return Node(**base)


def test_explanation_reads_as_a_sentence_without_jargon():
    text = explain(_node(), 0.231, "move", 1000, None, "O-O", "medium")
    assert text.startswith("You played 4.Nxe5 9 times and scored 11%")
    assert "players at this level score 23% with it" in text
    assert "points of results given away" in text
    for jargon in ("centipawn", "cp", "EPD", "FEN", "MultiPV"):
        assert jargon not in text


def test_explanation_says_so_when_the_evidence_is_thin():
    text = explain(_node(wins=0, draws=0, losses=3), 0.45, "position", 200, None, "", "low")
    assert "treat it as a hint" in text


def test_explanation_names_black_moves_with_the_right_notation():
    text = explain(_node(player_color="black"), None, "", 0, None, "", "medium")
    assert text.startswith("You played 4...Nxe5")


def test_percentages_round_the_same_way_the_browser_does():
    """Python rounds halves to even, JavaScript rounds them up. Left alone, the same
    figure appears as 62% in the sentence and 63% in the table beside it."""
    text = explain(_node(wins=1, draws=1, losses=8), 0.625, "position", 200, None, "", "medium")
    assert "63%" in text and "62%" not in text
