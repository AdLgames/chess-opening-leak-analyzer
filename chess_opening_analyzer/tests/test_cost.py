"""The cost formula: what a leak is worth, and why.

Two measurements go in — how your results compare with the book, and what the
engine says the move handed over — and one ranking number comes out. These pin
the parts that are easy to get subtly wrong and impossible to notice afterwards,
because a mis-weighted cost does not fail, it just ranks the wrong move first.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from chessopening.analyze import ENGINE_WEIGHT, node_severity  # noqa: E402
from chessopening.engine import PROB_CLAMP_CP, PositionEval, cp_to_prob  # noqa: E402


def _eval(best_cp: int, played_cp: int) -> PositionEval:
    return PositionEval(fen="", played_uci="", played_san="", mover="white",
                        best_cp=best_cp, played_cp=played_cp,
                        eval_drop_cp=best_cp - played_cp, played_rank=None,
                        alternatives=[], depth=12)


# ------------------------------------------------------- centipawns to results
def test_level_is_an_even_result():
    assert cp_to_prob(0) == pytest.approx(0.5)


def test_more_advantage_is_never_a_worse_expectation():
    probs = [cp_to_prob(cp) for cp in range(-800, 801, 50)]
    assert probs == sorted(probs)


def test_absurd_evaluations_are_clamped_not_overflowed():
    """A forced mate reports as a huge score; it must not run off the end."""
    assert cp_to_prob(10 ** 9) == cp_to_prob(PROB_CLAMP_CP)
    assert cp_to_prob(-10 ** 9) == cp_to_prob(-PROB_CLAMP_CP)
    assert 0.0 < cp_to_prob(10 ** 9) < 1.0


def test_a_pawn_costs_far_more_at_level_than_when_winning():
    """The whole reason for the change: pawns are not linear in what they cost.

    Losing one from level takes 64% to 50%. Losing one at +6.0 takes 96.9% to
    94.7%. The old per-pawn term charged those the same.
    """
    at_level = _eval(0, -100).win_prob_drop
    when_winning = _eval(600, 500).win_prob_drop
    assert at_level > when_winning * 5
    assert _eval(0, -100).eval_drop_pawns == _eval(600, 500).eval_drop_pawns


# --------------------------------------------------------------------- netting
def test_results_and_engine_are_netted_before_the_floor():
    """Outscoring the book cancels the engine's objection instead of ignoring it."""
    drop = _eval(0, -80).win_prob_drop
    engine_only = node_severity(None, drop)
    assert engine_only > 0
    # A player beating the book by more than the move hands over owes nothing.
    assert node_severity(engine_only + 0.05, drop) == 0.0


def test_outscoring_the_book_is_never_a_bonus():
    """Severity floors at zero: cost measures what is going wrong, not what is not."""
    assert node_severity(0.40, None) == 0.0
    assert node_severity(0.40, _eval(0, -50).win_prob_drop) == 0.0


def test_each_measurement_stands_on_its_own():
    assert node_severity(-0.20, None) == pytest.approx(0.20)
    assert node_severity(None, 0.10) == pytest.approx(ENGINE_WEIGHT * 0.10)
    assert node_severity(None, None) == 0.0


def test_the_engine_weight_preserves_the_old_balance_at_the_threshold():
    """1.8 is derived, not chosen.

    The old term charged 0.25 per pawn wherever it happened. Matching that at the
    blunder threshold in a balanced position — where opening decisions actually
    sit — is what keeps this change about *where* the engine matters rather than
    quietly changing *how much*.
    """
    threshold_pawns = 0.8
    old_term = 0.25 * threshold_pawns
    new_term = ENGINE_WEIGHT * _eval(0, -80).win_prob_drop
    assert new_term == pytest.approx(old_term, rel=0.15)
