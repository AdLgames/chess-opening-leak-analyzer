"""Spaced repetition: grading a move, widening the gap, and coming back after a miss.

Intervals are checked against hand-computed SM-2 values rather than captured output, so a
deliberate change to the schedule shows up as a deliberate change to a test.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.review import (  # noqa: E402
    GRADE_BEST,
    GRADE_GOOD,
    GRADE_OK,
    GRADE_REVEALED,
    GRADE_WEAK,
    ReviewStore,
    Schedule,
    describe_due,
    grade_for_loss,
    next_schedule,
    requeue_within_session,
)

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
EPD = "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq -"


# ---------------- Grading a move ----------------
def test_a_move_is_graded_by_what_it_gives_away():
    assert grade_for_loss(0) == GRADE_BEST
    assert grade_for_loss(20) == GRADE_BEST
    assert grade_for_loss(45) == GRADE_GOOD
    assert grade_for_loss(120) == GRADE_OK
    assert grade_for_loss(400) == GRADE_WEAK


def test_being_shown_the_answer_is_a_lapse_even_when_the_move_was_good():
    """Recognising a move is not recalling it, so revealing never counts as a pass."""
    assert grade_for_loss(0, revealed=True) == GRADE_REVEALED
    assert GRADE_REVEALED < GRADE_OK


# ---------------- The widening gap ----------------
def test_a_first_correct_answer_comes_back_tomorrow():
    s = next_schedule(Schedule(), GRADE_BEST, NOW)
    assert s.repetitions == 1
    assert s.interval_days == 1.0
    assert s.due_at == NOW + timedelta(days=1)


def test_the_second_correct_answer_jumps_to_six_days():
    s = next_schedule(Schedule(repetitions=1, interval_days=1.0), GRADE_BEST, NOW)
    assert s.repetitions == 2
    assert s.interval_days == 6.0


def test_after_that_the_gap_multiplies_by_the_ease():
    """Third pass onward: six days becomes six times the ease factor."""
    start = Schedule(repetitions=2, interval_days=6.0, ease=2.5)
    s = next_schedule(start, GRADE_BEST, NOW)
    assert s.ease == 2.6, "an easy recall raises the ease"
    assert s.interval_days == round(6.0 * 2.6, 2)


def test_struggling_shortens_the_gap_without_losing_progress():
    """A grade of 3 is still a pass, but the ease drops so the next gap is smaller."""
    s = next_schedule(Schedule(repetitions=2, interval_days=6.0, ease=2.5), GRADE_OK, NOW)
    assert s.repetitions == 3
    assert s.ease < 2.5
    assert s.interval_days < 6.0 * 2.5


def test_ease_never_falls_below_the_floor():
    """Past this point the interval stops growing and the position just churns."""
    s = Schedule(ease=1.3, repetitions=5, interval_days=30)
    for _ in range(5):
        s = next_schedule(s, GRADE_WEAK, NOW)
    assert s.ease == 1.3


def test_a_miss_brings_the_position_back_tomorrow():
    s = next_schedule(Schedule(repetitions=4, interval_days=40.0), GRADE_WEAK, NOW)
    assert s.interval_days == 1.0
    assert s.due_at == NOW + timedelta(days=1)
    assert s.repetitions == 0, "the streak is broken"
    assert s.lapses == 1


def test_a_lapse_is_counted_but_the_ease_carries_over():
    """Deliberately not a fresh card: the player has met this line before, and the point
    is to repair it rather than pretend otherwise."""
    first = next_schedule(Schedule(repetitions=3, interval_days=20.0, ease=2.5), GRADE_WEAK, NOW)
    second = next_schedule(first, GRADE_WEAK, NOW)
    assert second.lapses == 2
    assert second.ease < first.ease


def test_grades_outside_the_range_are_clamped_rather_than_trusted():
    assert next_schedule(Schedule(), 99, NOW).repetitions == 1
    assert next_schedule(Schedule(), -5, NOW).lapses == 1


# ---------------- Within one sitting ----------------
def test_a_missed_position_returns_later_in_the_same_session():
    queue = ["a", "b", "c", "d", "e"]
    assert requeue_within_session(queue, 0, gap=3) == ["b", "c", "d", "a", "e"]


def test_requeueing_near_the_end_puts_it_last_rather_than_off_the_end():
    assert requeue_within_session(["a", "b", "c"], 1, gap=5) == ["a", "c", "b"]


def test_requeueing_leaves_a_queue_of_one_alone():
    assert requeue_within_session(["only"], 0) == ["only"]


def test_an_out_of_range_index_is_survived():
    assert requeue_within_session(["a", "b"], 7) == ["a", "b"]
    assert requeue_within_session([], 0) == []


# ---------------- Persistence ----------------
def test_a_position_starts_due_immediately(tmp_path):
    store = ReviewStore(str(tmp_path / "state.sqlite"))
    store.enrol(EPD, "white", uci="f1c4", san="Bc4", opening="Italian Game", now=NOW)
    due = store.due(NOW)
    assert [d["san"] for d in due] == ["Bc4"]


def test_a_correct_answer_takes_it_out_of_today(tmp_path):
    store = ReviewStore(str(tmp_path / "state.sqlite"))
    store.enrol(EPD, "white", uci="f1c4", san="Bc4", now=NOW)
    store.record(EPD, "white", "f1c4", GRADE_BEST, cp_loss=0, now=NOW)
    assert store.due(NOW) == []
    assert len(store.due(NOW + timedelta(days=2))) == 1, "and back once the gap has passed"


def test_a_miss_keeps_it_in_tomorrow(tmp_path):
    store = ReviewStore(str(tmp_path / "state.sqlite"))
    store.enrol(EPD, "white", uci="f1c4", san="Bc4", now=NOW)
    store.record(EPD, "white", "f3e5", GRADE_WEAK, cp_loss=310, now=NOW)
    assert store.due(NOW) == []
    assert len(store.due(NOW + timedelta(days=1, hours=1))) == 1


def test_enrolling_again_does_not_reset_progress(tmp_path):
    """A new run re-offers the same positions; that must not wipe the schedule."""
    path = str(tmp_path / "state.sqlite")
    store = ReviewStore(path)
    store.enrol(EPD, "white", uci="f1c4", san="Bc4", now=NOW)
    store.record(EPD, "white", "f1c4", GRADE_BEST, now=NOW)
    store.enrol(EPD, "white", uci="f1c4", san="Bc4", now=NOW)
    assert store.schedule_for(EPD, "white").repetitions == 1
    assert store.due(NOW) == [], "still not due today"


def test_attempts_are_kept_as_a_history(tmp_path):
    store = ReviewStore(str(tmp_path / "state.sqlite"))
    store.record(EPD, "white", "f3e5", GRADE_WEAK, cp_loss=310, now=NOW)
    store.record(EPD, "white", "f1c4", GRADE_BEST, cp_loss=5, now=NOW + timedelta(days=1))
    history = store.history(EPD, "white")
    assert [h["grade"] for h in history] == [GRADE_BEST, GRADE_WEAK], "newest first"
    assert history[0]["cp_loss"] == 5


def test_progress_separates_what_is_known_from_what_is_still_being_learned(tmp_path):
    store = ReviewStore(str(tmp_path / "state.sqlite"))
    store.enrol(EPD, "white", san="Bc4", now=NOW)
    moment = NOW
    for _ in range(4):  # four clean recalls: 1, 6, ~16, ~42 days
        store.record(EPD, "white", "f1c4", GRADE_BEST, now=moment)
        moment += timedelta(days=store.schedule_for(EPD, "white").interval_days)
    stats = store.progress(NOW)
    assert stats["tracked"] == 1
    assert stats["known"] == 1, "recalled repeatedly, with the gap now in weeks"
    assert stats["learning"] == 0
    assert stats["accuracy_pct"] == 100.0


def test_progress_on_an_empty_store_reports_nothing_rather_than_dividing_by_zero(tmp_path):
    stats = ReviewStore(str(tmp_path / "state.sqlite")).progress(NOW)
    assert stats == {"tracked": 0, "due": 0, "known": 0, "learning": 0,
                     "attempts": 0, "accuracy_pct": None}


def test_a_position_can_be_dropped(tmp_path):
    store = ReviewStore(str(tmp_path / "state.sqlite"))
    store.enrol(EPD, "white", san="Bc4", now=NOW)
    store.record(EPD, "white", "f1c4", GRADE_BEST, now=NOW)
    assert store.forget(EPD, "white") is True
    assert store.due(NOW + timedelta(days=365)) == []
    assert store.history(EPD, "white") == []
    assert store.forget(EPD, "white") is False


# ---------------- Saying when ----------------
@pytest.mark.parametrize("days,expected", [
    (0.1, "again today"),
    (1, "again tomorrow"),
    (5, "again in 5 days"),
    (21, "again in 3 weeks"),
    (90, "again in 3 months"),
])
def test_the_next_review_is_described_in_words(days, expected):
    schedule = Schedule(due_at=NOW + timedelta(days=days))
    assert describe_due(schedule, NOW) == expected


def test_an_unscheduled_position_is_due_now():
    assert describe_due(Schedule()) == "due now"
