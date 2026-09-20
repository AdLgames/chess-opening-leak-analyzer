"""Runs compared over time: what got fixed, what appeared, and when not to trust it."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.history import HistoryStore, diff_runs  # noqa: E402

FEN_A = "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
FEN_B = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"


def leak(epd: str, uci: str, lost: float, color: str = "white", san: str = "Nxe5") -> dict:
    return {"epd": epd, "color": color, "uci": uci, "san": san,
            "opening": "Italian Game", "line": "", "category": "practical",
            "lost_points": lost}


def run(games: int = 200, leaks: int = 2, lost: float = 5.0, run_id: int = 1) -> dict:
    return {"id": run_id, "created_at": "2026-08-01 12:00", "games": games,
            "leaks": leaks, "lost_points": lost}


# ---------------- What changed ----------------
def test_a_leak_that_is_gone_counts_as_fixed():
    before = [leak("a", "f3e5", 4.0), leak("b", "g1f3", 2.0)]
    after = [leak("b", "g1f3", 2.0)]
    d = diff_runs(run(), before, run(run_id=2), after)
    assert [r["epd"] for r in d["fixed"]] == ["a"]
    assert d["points_recovered"] == 4.0
    assert d["new"] == []


def test_a_leak_that_was_not_there_before_counts_as_new():
    d = diff_runs(run(), [leak("a", "f3e5", 4.0)], run(run_id=2),
                  [leak("a", "f3e5", 4.0), leak("c", "d2d4", 1.0)])
    assert [r["epd"] for r in d["new"]] == ["c"]
    assert d["fixed"] == []


def test_the_same_move_in_a_different_position_is_a_different_leak():
    """Keyed on the position, not the move's name — 2.Nf3 in the Sicilian is not 2.Nf3
    in the King's Pawn."""
    d = diff_runs(run(), [leak(FEN_A, "g1f3", 3.0)], run(run_id=2), [leak(FEN_B, "g1f3", 3.0)])
    assert len(d["fixed"]) == 1 and len(d["new"]) == 1


def test_a_line_that_got_materially_worse_is_called_out():
    d = diff_runs(run(), [leak("a", "f3e5", 2.0)], run(run_id=2), [leak("a", "f3e5", 5.0)])
    assert [r["epd"] for r in d["worse"]] == ["a"]
    assert d["worse"][0]["was"] == 2.0


def test_a_line_that_improved_without_clearing_is_recorded_too():
    d = diff_runs(run(), [leak("a", "f3e5", 5.0)], run(run_id=2), [leak("a", "f3e5", 2.0)])
    assert [r["epd"] for r in d["better"]] == ["a"]


def test_ordinary_variance_is_not_reported_as_a_trend():
    """Without a threshold, every run would look like it moved."""
    d = diff_runs(run(), [leak("a", "f3e5", 4.0)], run(run_id=2), [leak("a", "f3e5", 4.3)])
    assert d["worse"] == [] and d["better"] == []
    assert d["unchanged"] == 1


def test_the_biggest_changes_come_first():
    before = [leak("a", "x", 1.0), leak("b", "y", 9.0), leak("c", "z", 4.0)]
    d = diff_runs(run(), before, run(run_id=2), [])
    assert [r["epd"] for r in d["fixed"]] == ["b", "c", "a"]


# ---------------- When not to trust it ----------------
def test_runs_over_very_different_game_counts_are_not_compared():
    """A leak that vanished because it was fixed and one that vanished because this run
    read a fifth as many games look identical from the diff alone."""
    d = diff_runs(run(games=200), [leak("a", "f3e5", 4.0)], run(games=40, run_id=2), [])
    assert d["comparable"] is False
    assert "too different to compare fairly" in d["headline"]


def test_similar_game_counts_are_compared():
    d = diff_runs(run(games=200), [leak("a", "f3e5", 4.0)], run(games=180, run_id=2), [])
    assert d["comparable"] is True
    assert "gone since last time" in d["headline"]


def test_the_headline_says_what_happened_in_words():
    fixed_only = diff_runs(run(), [leak("a", "x", 3.0)], run(run_id=2), [])
    assert "Nothing new appeared" in fixed_only["headline"]

    both = diff_runs(run(), [leak("a", "x", 3.0)], run(run_id=2), [leak("b", "y", 1.0)])
    assert "gone" in both["headline"] and "new" in both["headline"]

    worse_only = diff_runs(run(), [], run(run_id=2), [leak("b", "y", 1.0)])
    assert "none of the old ones cleared" in worse_only["headline"]

    nothing = diff_runs(run(), [leak("a", "x", 3.0)], run(run_id=2), [leak("a", "x", 3.0)])
    assert nothing["headline"] == "Nothing changed since your last run."


# ---------------- Persistence ----------------
def test_a_run_is_stored_with_its_leaks(tmp_path):
    store = HistoryStore(str(tmp_path / "state.sqlite"))
    rows = [{"fen": FEN_A, "player_color": "white", "your_move_uci": "f3e5",
             "your_move": "Nxe5", "opening": "Italian Game", "variation_line": "e4 e5",
             "category": "objective", "lost_points": "4.0"}]
    run_id = store.save_run({"games": 200, "leaks": 1, "lost_points": 4.0}, rows,
                            player="me", source="username")
    stored = store.leaks_for(run_id)
    assert len(stored) == 1
    assert stored[0]["san"] == "Nxe5"
    assert stored[0]["epd"] == " ".join(FEN_A.split()[:4]), "stored as a position key"
    assert store.runs()[0]["games"] == 200


def test_one_run_alone_has_nothing_to_compare_against(tmp_path):
    store = HistoryStore(str(tmp_path / "state.sqlite"))
    store.save_run({"games": 100, "leaks": 0, "lost_points": 0}, [])
    assert store.compare_latest() is None


def test_two_runs_compare_newest_against_the_one_before(tmp_path):
    store = HistoryStore(str(tmp_path / "state.sqlite"))
    rows = [{"fen": FEN_A, "player_color": "white", "your_move_uci": "f3e5",
             "your_move": "Nxe5", "lost_points": "4.0"}]
    store.save_run({"games": 200, "leaks": 1, "lost_points": 4.0}, rows)
    store.save_run({"games": 200, "leaks": 0, "lost_points": 0.0}, [])
    d = store.compare_latest()
    assert len(d["fixed"]) == 1
    assert d["points_recovered"] == 4.0
    assert d["current"]["leaks"] == 0


def test_the_headline_reads_as_english_for_a_single_change():
    """"1 of your leaks are gone" is the kind of thing that makes a tool feel unfinished."""
    d = diff_runs(run(), [leak("a", "x", 3.0)], run(run_id=2), [])
    assert d["headline"].startswith("One of your leaks is gone")
    many = diff_runs(run(), [leak("a", "x", 3.0), leak("b", "y", 1.0)], run(run_id=2), [])
    assert many["headline"].startswith("2 of your leaks are gone")
