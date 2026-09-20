"""Comparing a player against players of their own strength."""
from __future__ import annotations

import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.bands import ALL, band_for, label, neighbours  # noqa: E402
from chessopening.localdb import SCHEMA, LocalOpeningDatabase  # noqa: E402

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"


# ---------------- Which band ----------------
def test_a_rating_lands_in_its_band():
    assert band_for(1450) == "1200-1600"
    assert band_for(1600) == "1600-2000", "the boundary belongs to the band above"
    assert band_for(900) == "u1200"


def test_a_very_strong_player_is_not_dropped_off_the_end():
    assert band_for(2900) == "2400+"


def test_no_rating_means_no_band_rather_than_a_guess():
    """Plenty of exports carry no Elo. Inventing one would silently compare the player
    against the wrong population."""
    for value in (None, "", 0, -1, "unrated"):
        assert band_for(value) == ALL


def test_widening_goes_outward_before_it_goes_to_everybody():
    """A comparison against the right population with eight games behind it is worse than
    one against a slightly wrong population with eight hundred — but the near-neighbours
    should still be tried before everybody."""
    order = neighbours("1600-2000")
    assert order[0] == "1600-2000"
    assert set(order[1:3]) == {"1200-1600", "2000-2400"}
    assert order[-1] == ALL


def test_the_labels_are_readable():
    assert label("u1200") == "under 1200"
    assert label(ALL) == "all ratings"


# ---------------- Reading a banded book ----------------
def book(tmp_path, rows: list[tuple], banded: bool = True) -> str:
    """`rows` are (uci, san, band, white, draws, black)."""
    path = str(tmp_path / "book.sqlite")
    con = sqlite3.connect(path)
    if banded:
        con.executescript(SCHEMA)
        con.executemany(
            "INSERT INTO moves (pos, uci, band, san, white, draws, black, rating_sum) "
            "VALUES (?,?,?,?,?,?,?,0)",
            [(START, uci, band, san, w, d, b) for uci, san, band, w, d, b in rows],
        )
    else:
        # The shape of every book built before bands existed.
        con.executescript(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);"
            "CREATE TABLE moves (pos TEXT, uci TEXT, san TEXT, white INT, draws INT,"
            "  black INT, rating_sum INT, PRIMARY KEY (pos, uci));"
            "CREATE TABLE openings (pos TEXT PRIMARY KEY, eco TEXT, name TEXT);"
        )
        con.executemany(
            "INSERT INTO moves (pos, uci, san, white, draws, black, rating_sum) "
            "VALUES (?,?,?,?,?,?,0)",
            [(START, uci, san, w, d, b) for uci, san, band, w, d, b in rows if band == ALL],
        )
    con.commit()
    con.close()
    return path


def test_a_player_is_compared_against_their_own_band(tmp_path):
    """The same move can be a fine practical choice at 1400 and nothing at master level."""
    path = book(tmp_path, [
        ("e2e4", "e4", ALL, 500, 0, 500),          # 50% over everybody
        ("e2e4", "e4", "1200-1600", 700, 0, 300),  # 70% among club players
    ])
    db = LocalOpeningDatabase(path)
    assert db.lookup_epd(START, band="1200-1600").score_for("white") == 0.7
    assert db.lookup_epd(START).score_for("white") == 0.5


def test_the_band_actually_used_is_reported(tmp_path):
    """Not always the one asked for, so the interface must not imply otherwise."""
    path = book(tmp_path, [("e2e4", "e4", ALL, 500, 0, 500),
                           ("e2e4", "e4", "1200-1600", 700, 0, 300)])
    db = LocalOpeningDatabase(path)
    assert db.lookup_epd(START, band="1200-1600").band == "1200-1600"


def test_a_band_too_thin_to_say_anything_widens(tmp_path):
    """Eight games in exactly the right population is not a comparison."""
    path = book(tmp_path, [
        ("e2e4", "e4", ALL, 5000, 0, 5000),
        ("e2e4", "e4", "1200-1600", 4, 0, 4),
        ("e2e4", "e4", "1600-2000", 600, 0, 400),
    ])
    db = LocalOpeningDatabase(path)
    got = db.lookup_epd(START, band="1200-1600", min_band_games=200)
    assert got.band == "1600-2000", "widened to the neighbour, not straight to everybody"
    assert got.games == 1000


def test_widening_ends_at_everybody(tmp_path):
    path = book(tmp_path, [("e2e4", "e4", ALL, 5000, 0, 5000),
                           ("e2e4", "e4", "1200-1600", 4, 0, 4)])
    db = LocalOpeningDatabase(path)
    assert db.lookup_epd(START, band="1200-1600", min_band_games=200).band == ALL


def test_a_book_with_no_bands_answers_exactly_as_before(tmp_path):
    """The shipped book is one of these, and it must keep working with no rebuild."""
    path = book(tmp_path, [("e2e4", "e4", ALL, 500, 0, 500)], banded=False)
    db = LocalOpeningDatabase(path)
    assert db.has_bands is False
    got = db.lookup_epd(START, band="1200-1600")
    assert got.score_for("white") == 0.5
    assert got.band == ALL


def test_an_unbanded_book_is_not_rewritten_when_it_is_opened(tmp_path):
    """It is the player's file. Reading it should not migrate it behind their back."""
    path = book(tmp_path, [("e2e4", "e4", ALL, 10, 0, 10)], banded=False)
    LocalOpeningDatabase(path)
    con = sqlite3.connect(path)
    columns = {r[1] for r in con.execute("PRAGMA table_info(moves)")}
    assert "band" not in columns


def test_a_banded_book_holding_only_all_rows_is_not_claimed_as_banded(tmp_path):
    path = book(tmp_path, [("e2e4", "e4", ALL, 500, 0, 500)])
    assert LocalOpeningDatabase(path).has_bands is False


def test_the_average_rating_behind_a_move_is_available(tmp_path):
    path = str(tmp_path / "b.sqlite")
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.execute("INSERT INTO moves (pos, uci, band, san, white, draws, black, rating_sum) "
                "VALUES (?,?,?,?,?,?,?,?)", (START, "e2e4", ALL, "e4", 6, 0, 4, 16000))
    con.commit()
    con.close()
    [move] = LocalOpeningDatabase(path).lookup_epd(START).moves
    assert move.average_rating == 1600


def test_a_move_with_no_recorded_ratings_reports_none(tmp_path):
    path = book(tmp_path, [("e2e4", "e4", ALL, 6, 0, 4)])
    [move] = LocalOpeningDatabase(path).lookup_epd(START).moves
    assert move.average_rating is None


# ---------------- Reading the player's own rating ----------------
def test_the_players_rating_comes_from_their_side_of_the_board():
    from chessopening.pgn_loader import _rating
    headers = {"WhiteElo": "1820", "BlackElo": "1410"}
    assert _rating(headers, "white") == 1820
    assert _rating(headers, "black") == 1410


def test_a_missing_or_nonsense_rating_is_not_invented():
    from chessopening.pgn_loader import _rating
    for value in ("", "?", "-", "unrated", "0", "99999"):
        assert _rating({"WhiteElo": value}, "white") is None
    assert _rating({}, "white") is None
