"""Roll-up contract: the numbers the dashboards read out of a finished run.

Pure data, no engine and no python-chess, so it runs anywhere:
`python -m pytest tests -q` or `python tests/test_summary.py`.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.summary import family_of, summarise  # noqa: E402

ROWS = [
    {"cost": "6.0", "flag": "blunder+underperforming", "eco": "C50", "opening": "Italian Game",
     "your_games": "12", "your_score_pct": "31.0", "db_move_score_pct": "52.0",
     "db_position_score_pct": "50.0", "lost_points": "2.5", "eval_drop_pawns": "1.2",
     "player_color": "white"},
    {"cost": "0.4", "flag": "unfamiliar+thin", "eco": "B22", "opening": "Sicilian, Alapin",
     "your_games": "3", "your_score_pct": "33.0", "db_move_score_pct": "48.0",
     "db_position_score_pct": "49.0", "lost_points": "0.5", "eval_drop_pawns": "",
     "player_color": "black"},
]
STATS = {"games": 140, "nodes": 320, "repeated": 48, "repeated_games": 410}
EXPLORER_STATS = {
    **STATS,
    "opening_profiles": {
        "openings": [{"key": "white:Italian Game", "family": "Italian Game", "first_break": 4}],
        "break_moves": [{"move_number": 4, "leaks": 1, "games": 12}],
        "worst_against": ["white:Italian Game"],
    },
    "traps": {"catalogue": 15, "met": 3, "fell": 1, "traps": [{"key": "fried_liver"}]},
}


def test_totals_and_flag_counts():
    s = summarise(ROWS, STATS)
    assert s["games"] == 140 and s["judged"] == 48
    assert s["judged_games"] == 410, "coverage needs the games behind judged decisions"
    assert s["leaks"] == 2
    assert s["cost"] == 6.4
    assert s["lost_points"] == 3.0
    assert s["blunders"] == 1
    assert s["flags"] == {"blunder": 1, "underperforming": 1, "unfamiliar": 1, "thin": 1}
    assert s["white_leaks"] == 1 and s["black_leaks"] == 1


def test_openings_are_ranked_by_points_shed():
    s = summarise(ROWS, STATS)
    assert [o["opening"] for o in s["by_opening"]] == ["Italian Game", "Sicilian, Alapin"]
    assert s["by_opening"][0]["games"] == 12


def test_a_family_is_the_name_before_the_colon():
    """ECO names are "Family: Variation, Sub-variation"."""
    assert family_of("Italian Game: Giuoco Piano") == "Italian Game"
    assert family_of("Sicilian Defense: Najdorf, English Attack") == "Sicilian Defense"
    assert family_of("Queen's Gambit Accepted") == "Queen's Gambit Accepted"
    assert family_of("") == "Unclassified"
    assert family_of("  ") == "Unclassified"
    # A name that is nothing but a colon still has to come back as something.
    assert family_of(":") == ":"


def test_variations_roll_up_into_one_family():
    """Two branches of the same opening are one problem, not two small ones."""
    rows = [
        {"cost": "3.0", "flag": "underperforming", "eco": "C50",
         "opening": "Italian Game: Giuoco Piano", "your_games": "10",
         "your_score_pct": "40", "db_move_score_pct": "50",
         "db_position_score_pct": "50", "lost_points": "1.0",
         "eval_drop_pawns": "", "player_color": "white"},
        {"cost": "2.0", "flag": "underperforming", "eco": "C50",
         "opening": "Italian Game: Giuoco Pianissimo", "your_games": "6",
         "your_score_pct": "44", "db_move_score_pct": "50",
         "db_position_score_pct": "50", "lost_points": "0.5",
         "eval_drop_pawns": "", "player_color": "white"},
    ]
    fams = summarise(rows, STATS)["by_family"]
    assert [f["family"] for f in fams] == ["Italian Game"]
    fam = fams[0]
    assert fam["cost"] == 5.0 and fam["lost_points"] == 1.5
    assert fam["leaks"] == 2 and fam["games"] == 16
    assert [v["opening"] for v in fam["variations"]] == [
        "Italian Game: Giuoco Piano", "Italian Game: Giuoco Pianissimo"]
    assert fam["variations"][0]["cost"] == 3.0


def test_families_are_ranked_by_cost_not_points_shed():
    """The two orders genuinely differ, which is the whole reason to pick one.

    Points shed is the raw figure; a family resting on one thin sample can shed
    more of them than a well-evidenced one while being far less worth repairing.
    """
    rows = [
        {"cost": "1.0", "flag": "thin", "eco": "B01", "opening": "Scandinavian Defense",
         "your_games": "3", "your_score_pct": "0", "db_move_score_pct": "50",
         "db_position_score_pct": "50", "lost_points": "9.0", "eval_drop_pawns": "",
         "player_color": "black"},
        {"cost": "8.0", "flag": "underperforming", "eco": "C50", "opening": "Italian Game",
         "your_games": "30", "your_score_pct": "40", "db_move_score_pct": "50",
         "db_position_score_pct": "50", "lost_points": "2.0", "eval_drop_pawns": "",
         "player_color": "white"},
    ]
    s = summarise(rows, STATS)
    assert [f["family"] for f in s["by_family"]] == ["Italian Game", "Scandinavian Defense"]
    # by_opening still ranks the old way, so nothing reading it changes meaning
    assert [o["opening"] for o in s["by_opening"]] == ["Scandinavian Defense", "Italian Game"]


def test_the_explorer_payload_is_passed_through():
    s = summarise(ROWS, EXPLORER_STATS)
    assert s["explorer"]["openings"][0]["first_break"] == 4
    assert s["explorer"]["break_moves"] == [{"move_number": 4, "leaks": 1, "games": 12}]
    assert s["explorer"]["worst_against"] == ["white:Italian Game"]
    assert s["explorer"]["traps"]["fell"] == 1


def test_a_run_without_profiles_still_summarises():
    s = summarise(ROWS, STATS)
    assert s["explorer"] == {"openings": [], "break_moves": [], "worst_against": [], "traps": {}}


def test_missing_judged_games_does_not_break_older_runs():
    s = summarise(ROWS, {"games": 1, "nodes": 1, "repeated": 1})
    assert s["judged_games"] == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
