"""Per-opening profiles: the fold behind the explorer's personal view.

Pure data, no engine and no python-chess:
`python -m pytest tests -q` or `python tests/test_profiles.py`.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.profiles import build_profiles, epd_of, family  # noqa: E402


@dataclass
class FakeMove:
    san: str
    games: int
    score: float

    def score_for(self, colour):
        return self.score


@dataclass
class FakeStats:
    name: str = ""
    games: int = 4000
    score: float = 0.52
    moves: list = field(default_factory=list)

    def score_for(self, colour):
        return self.score


@dataclass
class FakePly:
    epd_before: str


@dataclass
class FakeGame:
    player_color: str
    player_score: float
    plies: list = field(default_factory=list)
    eco: str = ""
    opening: str = ""


@dataclass
class FakeNode:
    epd: str
    player_color: str
    n: int
    opening: str = ""


ROW = {
    "cost": "4.2", "flag": "blunder", "eco": "B22", "opening": "Sicilian Defense: Alapin, Barmen",
    "variation_line": "e4 c5 c3 d5 exd5 Qxd5 d4 Nf6 Nf3 Bg4 Be2 e6 h3", "move_number": "7",
    "ply": "13", "player_color": "white", "your_move": "h3",
    "fen": "rn2kb1r/pp3ppp/4pn2/8/3P2b1/2P2N1P/PP2BPP1/RNBQK2R b KQkq - 0 7",
    "your_games": "9", "your_score_pct": "38.0", "db_move_score_pct": "44.0",
    "engine_best_1": "Be3", "engine_best_1_db_score_pct": "56.0",
}


def _run(rows=(ROW,), **kw):
    stats = FakeStats(name="Sicilian Defense: Alapin")
    games = [FakeGame("white", 1.0, [FakePly("p1")]), FakeGame("white", 0.0, [FakePly("p1")]),
             FakeGame("white", 0.0, [FakePly("p1")])]
    nodes = [FakeNode("p1", "white", 9, "Sicilian Defense: Alapin")]
    defaults = dict(nodes=nodes, games=games, rows=list(rows),
                    pos_stats={"p1": stats, epd_of(ROW["fen"]): stats},
                    name_for=lambda epd: ("B22", "Sicilian Defense: Alapin, Barmen"))
    defaults.update(kw)
    return build_profiles(**defaults)


def test_variations_fold_into_one_family_per_colour():
    assert family("Sicilian Defense: Alapin, Barmen") == "Sicilian Defense"
    assert family("") == "Unclassified"
    out = _run()
    assert [p["key"] for p in out["openings"]] == ["white:Sicilian Defense"]
    prof = out["openings"][0]
    assert prof["games"] == 3 and prof["wins"] == 1 and prof["losses"] == 2
    assert prof["name"] == "Sicilian Defense: Alapin, Barmen", "the label keeps the full variation"


def test_your_record_is_reported_against_the_book_expectation():
    prof = _run()["openings"][0]
    assert prof["score_pct"] == 33.3          # 1 win, 2 losses
    assert prof["book_score_pct"] == 52.0     # what the book gets from the same positions
    assert prof["gap_pct"] == -18.7


def test_the_break_point_is_the_move_number_the_line_stops_holding():
    out = _run()
    prof = out["openings"][0]
    assert prof["first_break"] == 7
    assert prof["breaks"] == [{"move_number": 7, "games": 9}]
    assert out["break_moves"] == [{"move_number": 7, "leaks": 1, "games": 9}]


def test_the_engine_move_is_the_recommendation_when_the_run_had_one():
    leak = _run()["openings"][0]["leaks"][0]
    assert leak["play_instead"] == "Be3" and leak["instead_source"] == "engine"


def test_without_an_engine_the_book_supplies_the_recommendation():
    row = dict(ROW, engine_best_1="", engine_best_1_db_score_pct="")
    stats = FakeStats(name="Sicilian Defense: Alapin", moves=[
        FakeMove("h3", 400, 0.44), FakeMove("Be3", 900, 0.56), FakeMove("Nbd2", 5, 0.99),
    ])
    out = _run(rows=[row], pos_stats={"p1": stats, epd_of(ROW["fen"]): stats})
    leak = out["openings"][0]["leaks"][0]
    assert leak["play_instead"] == "Be3", "the thin 5-game move must not be recommended"
    assert leak["instead_source"] == "book" and leak["instead_score_pct"] == 56.0


def test_traps_attach_to_the_opening_they_belong_to():
    trap = {"key": "englund_qb4", "victim": "white", "opening": "Sicilian Defense"}
    out = _run(traps=[trap])
    assert out["openings"][0]["traps"] == ["englund_qb4"]


def test_a_thin_sample_is_not_called_a_weakness():
    games = [FakeGame("black", 0.0, [FakePly("p1")])]
    out = _run(games=games, rows=[])
    assert out["openings"][0]["games"] == 1
    assert out["worst_against"] == [], "one game is not evidence of a weak opening"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
