"""The book checker: it has to fail on the things that are silently wrong.

A bad book does not crash anything — it quietly compares every player against
everybody at once, or stops following theory five moves early. That is exactly
the class of problem worth a test, because nothing else will notice.
"""
from __future__ import annotations

import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from check_book import check  # noqa: E402


def book(path, *, filters="speeds=all elo=0-4000 max_moves=20", bands=("all", "1600-2000")):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE moves (pos TEXT, uci TEXT, band TEXT, san TEXT,
                            white INT, draws INT, black INT, rating_sum INT);
        CREATE TABLE openings (eco TEXT, name TEXT, pos TEXT);
    """)
    con.executemany("INSERT INTO meta VALUES (?, ?)",
                    [("games", "100"), ("source", "test"), ("filters", filters),
                     ("built_at", "2026-01-01")])
    for band in bands:
        con.execute("INSERT INTO moves VALUES ('epd', 'e2e4', ?, 'e4', 5, 1, 4, 1700)", (band,))
    con.execute("INSERT INTO openings VALUES ('C20', 'Kings Pawn', 'epd')")
    con.commit()
    con.close()
    return str(path)


def test_a_good_book_passes(tmp_path, capsys):
    assert check(book(tmp_path / "ok.sqlite"), 20) == 0
    assert "OK" in capsys.readouterr().out


def test_a_shallow_book_fails_and_says_by_how_much(tmp_path, capsys):
    path = book(tmp_path / "shallow.sqlite", filters="speeds=all elo=0-4000 max_moves=15")
    assert check(path, 20) == 1
    out = capsys.readouterr().out
    assert "built to move 15" in out and "move 20 was expected" in out


def test_a_book_with_no_bands_fails(tmp_path, capsys):
    path = str(tmp_path / "nobands.sqlite")
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE moves (pos TEXT, uci TEXT, san TEXT, white INT, draws INT,
                            black INT, rating_sum INT);
        CREATE TABLE openings (eco TEXT, name TEXT, pos TEXT);
    """)
    con.execute("INSERT INTO meta VALUES ('filters', 'max_moves=20')")
    con.execute("INSERT INTO moves VALUES ('epd', 'e2e4', 'e4', 5, 1, 4, 1700)")
    con.commit()
    con.close()
    assert check(path, 20) == 1
    assert "no band column" in capsys.readouterr().out


def test_only_all_rows_is_not_good_enough(tmp_path, capsys):
    """A band column full of nothing but `all` is the same problem, hidden."""
    assert check(book(tmp_path / "allonly.sqlite", bands=("all",)), 20) == 1
    assert "nothing to compare a rated player against" in capsys.readouterr().out


def test_a_book_with_no_all_rows_fails(tmp_path, capsys):
    assert check(book(tmp_path / "noall.sqlite", bands=("1600-2000",)), 20) == 1
    assert "no 'all' rows" in capsys.readouterr().out


def test_an_lfs_pointer_is_named_as_one(tmp_path, capsys):
    """The commonest way to end up with no book at all."""
    pointer = tmp_path / "pointer.sqlite"
    pointer.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\n")
    assert check(str(pointer), 20) == 1
    assert "Git LFS pointer" in capsys.readouterr().out


def test_a_missing_file_is_not_a_traceback(tmp_path, capsys):
    assert check(str(tmp_path / "absent.sqlite"), 20) == 1
    assert "no such file" in capsys.readouterr().out


def test_an_unrecorded_depth_is_a_failure_not_a_shrug(tmp_path, capsys):
    path = book(tmp_path / "nodepth.sqlite", filters="speeds=all elo=0-4000")
    assert check(path, None) == 1
    assert "does not record max_moves" in capsys.readouterr().out


def test_a_rating_filtered_book_leaves_most_bands_empty(tmp_path, capsys):
    """Why the build command no longer filters by rating.

    Filtering the corpus to 1500-2100 and then asking it for bands gives bands
    that mostly do not exist. The checker cannot know the corpus, but it can see
    that only one real band came out, which is the symptom.
    """
    path = book(tmp_path / "narrow.sqlite", bands=("all", "1600-2000"))
    assert check(path, 20) == 0          # usable, but only just
    out = capsys.readouterr().out
    assert "1600-2000" in out and "all" in out


def test_a_book_spanning_the_bands_reports_them_all(tmp_path, capsys):
    path = book(tmp_path / "wide.sqlite",
                bands=("all", "u1200", "1200-1600", "1600-2000", "2000-2400", "2400+"))
    assert check(path, 20) == 0
    out = capsys.readouterr().out
    for band in ("u1200", "1200-1600", "1600-2000", "2000-2400", "2400+"):
        assert band in out
