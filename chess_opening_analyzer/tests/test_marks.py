"""The player's own decisions, and what the report may still say afterwards.

The rule being pinned here is the one that decides whether people keep trusting the tool:
committing to a move silences the argument about taste, and nothing else.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.marks import (  # noqa: E402
    Mark,
    MarkStore,
    filter_flags,
    load_marks,
    summarise_marks,
)

EPD = "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq -"
BC4 = "f1c4"


def committed(uci: str = BC4) -> Mark:
    return Mark(epd=EPD, color="white", uci=uci, san="Bc4", decision="committed")


def ignored(uci: str = BC4) -> Mark:
    return Mark(epd=EPD, color="white", uci=uci, san="Bc4", decision="ignored")


# ---------------- What survives a decision ----------------
def test_committing_silences_the_argument_about_taste():
    """"Others score better with something else" is exactly the complaint someone who has
    chosen their line does not need repeating."""
    assert filter_flags(["WINRATE_DECLINE"], committed(), BC4) is None
    assert filter_flags(["OFFBEAT_MOVE"], committed(), BC4) is None
    assert filter_flags(["WINRATE_DECLINE", "OFFBEAT_MOVE"], committed(), BC4) is None


def test_committing_does_not_silence_a_move_that_loses_material():
    """The one thing a preference cannot overrule: whether the position goes wrong."""
    assert filter_flags(["EVAL_DROP"], committed(), BC4) == ["EVAL_DROP"]
    assert filter_flags(["EVAL_DROP", "WINRATE_DECLINE"], committed(), BC4) == ["EVAL_DROP"]


def test_ignoring_silences_everything_including_an_engine_drop():
    """Committing is "this is my line"; ignoring is "I have seen this, stop showing me"."""
    assert filter_flags(["EVAL_DROP"], ignored(), BC4) is None
    assert filter_flags(["WINRATE_DECLINE"], ignored(), BC4) is None


def test_a_decision_applies_only_to_the_move_it_was_made_about():
    """Switching to a different move is a new choice, and gets judged on its own."""
    assert filter_flags(["WINRATE_DECLINE"], committed(BC4), "f1b5") == ["WINRATE_DECLINE"]
    assert filter_flags(["EVAL_DROP"], ignored(BC4), "f1b5") == ["EVAL_DROP"]


def test_no_decision_changes_nothing():
    assert filter_flags(["WINRATE_DECLINE"], None, BC4) == ["WINRATE_DECLINE"]


# ---------------- Storage ----------------
def test_a_decision_is_remembered(tmp_path):
    store = MarkStore(str(tmp_path / "state.sqlite"))
    store.set(EPD, "white", BC4, "committed", san="Bc4")
    assert load_marks(str(tmp_path / "state.sqlite"))[(EPD, "white")].decision == "committed"


def test_changing_your_mind_replaces_the_earlier_decision(tmp_path):
    path = str(tmp_path / "state.sqlite")
    store = MarkStore(path)
    store.set(EPD, "white", BC4, "committed", san="Bc4")
    store.set(EPD, "white", BC4, "ignored", san="Bc4")
    marks = store.all()
    assert len(marks) == 1
    assert marks[(EPD, "white")].decision == "ignored"


def test_the_two_colours_are_decided_separately(tmp_path):
    """The same position can be reached from either side, and the choices are unrelated."""
    store = MarkStore(str(tmp_path / "state.sqlite"))
    store.set(EPD, "white", BC4, "committed")
    store.set(EPD, "black", "e7e5", "ignored")
    assert len(store.all()) == 2


def test_a_decision_can_be_undone(tmp_path):
    store = MarkStore(str(tmp_path / "state.sqlite"))
    store.set(EPD, "white", BC4, "committed")
    assert store.clear(EPD, "white") is True
    assert store.all() == {}
    assert store.clear(EPD, "white") is False, "nothing left to undo"


def test_an_unknown_decision_is_refused(tmp_path):
    store = MarkStore(str(tmp_path / "state.sqlite"))
    with pytest.raises(ValueError, match="decision must be one of"):
        store.set(EPD, "white", BC4, "maybe")


def test_no_file_yet_means_no_decisions(tmp_path):
    assert load_marks(str(tmp_path / "never-written.sqlite")) == {}


def test_the_listing_is_newest_first_and_renderable(tmp_path):
    store = MarkStore(str(tmp_path / "state.sqlite"))
    store.set(EPD, "white", BC4, "committed", san="Bc4", note="I like the Italian")
    rows = store.listing()
    assert rows[0]["san"] == "Bc4"
    assert rows[0]["note"] == "I like the Italian"
    assert rows[0]["created_at"]


def test_decisions_are_counted_by_kind():
    assert summarise_marks([committed(), ignored(), committed()]) == {"committed": 2, "ignored": 1}
