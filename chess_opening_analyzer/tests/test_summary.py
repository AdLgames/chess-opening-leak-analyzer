"""Roll-up contract: the numbers the dashboards read out of a finished run.

Pure data, no engine and no python-chess, so it runs anywhere:
`python -m pytest tests -q` or `python tests/test_summary.py`.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.summary import summarise  # noqa: E402

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


def test_missing_judged_games_does_not_break_older_runs():
    s = summarise(ROWS, {"games": 1, "nodes": 1, "repeated": 1})
    assert s["judged_games"] == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
