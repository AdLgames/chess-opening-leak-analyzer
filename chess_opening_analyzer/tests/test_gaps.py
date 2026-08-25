"""Answering a gap: what to prepare, and what the player has decided about it."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.explorer import MoveStats, PositionStats  # noqa: E402
from chessopening.marks import (  # noqa: E402
    GapStore, apply_gap_decisions, load_gap_decisions,
)
from chessopening.repertoire import best_reply  # noqa: E402

FEN = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
EPD = " ".join(FEN.split()[:4])


def move(uci: str, san: str, white: int, draws: int, black: int) -> MoveStats:
    return MoveStats(uci=uci, san=san, white=white, draws=draws, black=black)


def position(moves: list[MoveStats]) -> PositionStats:
    return PositionStats(
        eco="B20", name="Sicilian Defense",
        white=sum(m.white for m in moves), draws=sum(m.draws for m in moves),
        black=sum(m.black for m in moves), moves=moves,
    )


# ---------------- What to play in a position you have never faced ----------------
def test_the_book_supplies_an_answer_where_the_player_has_none():
    """A gap has no move of the player's to grade against — the target comes from the
    book, which knows what happened when other people stood here."""
    stats = position([move("g1f3", "Nf3", 60, 20, 20), move("b1c3", "Nc3", 20, 20, 60)])
    answer = best_reply(stats, "white")
    assert answer["san"] == "Nf3"
    assert answer["games"] == 100


def test_a_move_with_too_little_behind_it_is_not_an_answer_at_all():
    stats = position([move("a2a4", "a4", 3, 0, 0)])
    assert best_reply(stats, "white") is None


def test_a_position_the_book_has_never_seen_has_no_answer():
    assert best_reply(position([]), "white") is None


def test_the_answer_is_read_from_the_players_side():
    """The same move is good news for one side and bad for the other."""
    stats = position([move("g1f3", "Nf3", 80, 0, 20), move("b1c3", "Nc3", 20, 0, 80)])
    assert best_reply(stats, "white")["san"] == "Nf3"
    assert best_reply(stats, "black")["san"] == "Nc3"


def test_the_raw_and_the_shrunk_score_are_both_reported():
    """The interface should be able to show the record and the adjusted figure without
    passing one off as the other."""
    stats = position([move("g1f3", "Nf3", 60, 20, 20), move("b1c3", "Nc3", 100, 100, 200)])
    answer = best_reply(stats, "white")
    assert answer["raw_score_pct"] == 70.0
    assert answer["score_pct"] < answer["raw_score_pct"], "pulled toward the position average"


def test_a_sideline_nobody_plays_is_not_the_answer_either():
    """Shrinkage alone does not save us: a 12-game 100% still shrinks to about 71%, which
    beats a 1000-game 64% mainline. The share filter is what actually catches it."""
    stats = position([
        move("a2a4", "a4", 12, 0, 0),
        move("g1f3", "Nf3", 520, 240, 240),
    ])
    answer = best_reply(stats, "white")
    assert answer["san"] == "Nf3"
    assert answer["share_pct"] > 90


# ---------------- What the player decided about it ----------------
def gap(fen: str = FEN, color: str = "white", reply: str = "c5") -> dict:
    return {"fen": fen, "player_color": color, "reply": reply, "line": "1.e4 c5",
            "opening": "Sicilian Defense", "reach_pct": 19.0}


def test_an_ignored_gap_stops_being_listed(tmp_path):
    store = GapStore(str(tmp_path / "s.sqlite"))
    store.set(EPD, "white", "ignored")
    assert apply_gap_decisions([gap()], store.all()) == []


def test_a_gap_being_learned_stays_listed_and_says_so(tmp_path):
    """The point of the section is a queue being worked through, not a list of
    accusations that never shrinks."""
    store = GapStore(str(tmp_path / "s.sqlite"))
    store.set(EPD, "white", "learning")
    [out] = apply_gap_decisions([gap()], store.all())
    assert out["decision"] == "learning"
    assert out["reach_pct"] == 19.0, "the analysis itself is untouched"


def test_an_undecided_gap_is_left_alone(tmp_path):
    store = GapStore(str(tmp_path / "s.sqlite"))
    [out] = apply_gap_decisions([gap()], store.all())
    assert out["decision"] == ""


def test_a_decision_applies_to_one_colour_only(tmp_path):
    """Facing the Sicilian as White and reaching the same position as Black are two
    different problems."""
    store = GapStore(str(tmp_path / "s.sqlite"))
    store.set(EPD, "white", "ignored")
    assert len(apply_gap_decisions([gap(color="black")], store.all())) == 1


def test_a_decision_can_be_changed(tmp_path):
    store = GapStore(str(tmp_path / "s.sqlite"))
    store.set(EPD, "white", "ignored")
    store.set(EPD, "white", "practising")
    assert store.all()[(EPD, "white")] == "practising"
    assert len(store.listing()) == 1, "changed, not duplicated"


def test_a_decision_can_be_undone(tmp_path):
    store = GapStore(str(tmp_path / "s.sqlite"))
    store.set(EPD, "white", "ignored")
    assert store.clear(EPD, "white") is True
    assert store.all() == {}
    assert store.clear(EPD, "white") is False


def test_an_unknown_decision_is_refused(tmp_path):
    store = GapStore(str(tmp_path / "s.sqlite"))
    try:
        store.set(EPD, "white", "whatever")
    except ValueError as err:
        assert "learning" in str(err)
    else:
        raise AssertionError("an unrecognised decision should not be stored")


def test_no_decisions_on_file_means_no_decisions(tmp_path):
    assert load_gap_decisions(str(tmp_path / "nothing.sqlite")) == {}


def test_gap_decisions_and_move_marks_do_not_collide(tmp_path):
    """Both are keyed on (position, colour) but they mean different things, and one must
    not overwrite the other."""
    from chessopening.marks import MarkStore
    path = str(tmp_path / "s.sqlite")
    marks = MarkStore(path)
    marks.set(EPD, "white", "g1f3", "committed", san="Nf3")
    gaps = GapStore(path)
    gaps.set(EPD, "white", "ignored")
    assert marks.all()[(EPD, "white")].decision == "committed"
    assert gaps.all()[(EPD, "white")] == "ignored"
