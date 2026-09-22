"""What counts as a leak, and what counts as merely played.

These pin the definition itself rather than any one number it produces:

* the output holds every repeated decision, not only the ones that leak — a
  line you play well used to leave no trace at all;
* a leak still needs a real signal, and `thin` is never that signal;
* the opening window follows the book past the fixed cutoff, and says so when
  the book is too shallow to follow.

No engine and no network: the book is built from the sample PGNs, so the whole
module runs offline.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from chessopening.analyze import BOOK_CEILING_PLY, analyze  # noqa: E402
from chessopening.localdb import LocalOpeningDatabase  # noqa: E402
from chessopening.pgn_loader import find_pgn_files  # noqa: E402

PGN_DIR = os.path.join(ROOT, "sample_pgns")
PLAYER = "SamplePlayer"


def book(tmp_path, max_moves: int) -> str:
    """A local book built from the sample games, to a chosen depth."""
    from build_local_db import build  # noqa: PLC0415

    path = str(tmp_path / f"book-{max_moves}.sqlite")
    build(find_pgn_files(PGN_DIR), path, max_moves=max_moves, speeds=None,
          min_move_games=1, offline_eco=True)
    return path


def run(tmp_path, db_path: str, **kw):
    options = dict(pgn_dir=PGN_DIR, player=PLAYER, out_dir=str(tmp_path / "out"),
                   db="local", local_db_path=db_path, min_db_games=1, no_engine=True,
                   cache_dir=str(tmp_path / "cache"), log=lambda *a: None)
    options.update(kw)
    return analyze(**options)


def leak_rows(result) -> list[dict]:
    with open(result["report"], encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------ the tree
def test_the_output_keeps_lines_that_do_not_leak(tmp_path):
    result = run(tmp_path, book(tmp_path, 10))
    tree = result["tree"]
    leaks = leak_rows(result)

    assert tree, "no repeated decisions were recorded at all"
    clean = [r for r in tree if not r["flag"]]
    assert clean, "every repeated decision was flagged — the tree is not a tree"
    assert len(tree) > len(leaks), "the tree must be wider than the leak table"
    # and the tree is written next to the report, not only returned in memory
    with open(result["tree_path"], encoding="utf-8") as fh:
        assert len(list(csv.DictReader(fh))) == len(tree)


def test_a_clean_line_carries_its_numbers_not_just_its_name(tmp_path):
    """A line you play well is only useful in the output if it is legible."""
    result = run(tmp_path, book(tmp_path, 10))
    clean = [r for r in result["tree"] if not r["flag"] and r["in_book"] == "yes"]
    assert clean
    row = clean[0]
    assert int(row["your_games"]) >= 3
    assert row["your_score_pct"] and row["db_position_score_pct"]
    assert float(row["cost"]) == 0.0, "a decision with no flag has no cost"


def test_the_leak_table_is_a_strict_subset_of_the_tree(tmp_path):
    result = run(tmp_path, book(tmp_path, 10))
    tree_keys = {(r["fen"], r["your_move"]) for r in result["tree"]}
    for row in leak_rows(result):
        assert (row["fen"], row["your_move"]) in tree_keys
        assert row["flag"], "a row reached the leak table with no flag"


def test_a_line_seen_twice_is_recorded_but_cannot_leak(tmp_path):
    """The rare-line blind spot, made visible.

    A decision below `min_games` is not judged — but it used to vanish entirely,
    which is why a tricky line met once a month could never surface. It is now
    in the tree, marked ineligible, with the count that says why.
    """
    result = run(tmp_path, book(tmp_path, 10), min_games=11)
    ineligible = [r for r in result["tree"] if r["eligible"] == "no"]
    assert ineligible, "no decision fell below the threshold to test with"
    for row in ineligible:
        assert int(row["your_games"]) < 11
        assert row["flag"] == "", "an ineligible decision was flagged anyway"
    assert all(int(r["your_games"]) >= 11
               for r in result["tree"] if r["eligible"] == "yes")
    # and none of them reached the leak table
    keys = {(r["fen"], r["your_move"]) for r in ineligible}
    assert not any((r["fen"], r["your_move"]) in keys for r in leak_rows(result))


# ----------------------------------------------------------- what qualifies
def test_thin_never_qualifies_a_decision_on_its_own(tmp_path):
    """`thin` is a caveat on a leak, never the reason it is one."""
    result = run(tmp_path, book(tmp_path, 10), min_games=1, thin_games=99)
    for row in leak_rows(result):
        flags = row["flag"].split("+")
        assert flags != ["thin"]
        assert set(flags) - {"thin"}, f"only caveats in {row['flag']!r}"
    # with thin_games that high, every leak found should carry the caveat
    assert all("thin" in r["flag"] for r in leak_rows(result))


def test_an_unflagged_decision_never_reaches_the_leak_table(tmp_path):
    result = run(tmp_path, book(tmp_path, 10))
    assert all(r["flag"] for r in leak_rows(result))
    assert len(leak_rows(result)) == sum(1 for r in result["tree"] if r["flag"])


# ------------------------------------------------------------- the window
def test_the_book_extends_the_window_past_the_fixed_cutoff(tmp_path):
    """A deep main line should be followed while theory still covers it."""
    deep_book = book(tmp_path, 10)
    shallow = run(tmp_path / "a", deep_book, max_moves=3)
    assert shallow["tree"], "nothing judged at all"
    deepest = max(int(r["move_number"]) for r in shallow["tree"])
    assert deepest > 3, (
        f"the window stopped dead at the cutoff (deepest move {deepest}) — "
        "the book was not followed")
    assert deepest <= BOOK_CEILING_PLY // 2


def test_a_book_too_shallow_to_follow_says_so(tmp_path):
    """Following a book past its own depth is following nothing. Say it."""
    result = run(tmp_path, book(tmp_path, 3), max_moves=3)
    notes = " ".join(result.get("notes", []))
    assert "only goes to move 3" in notes, notes
    assert "--max-moves" in notes, "the note should say how to fix it"
    assert max(int(r["move_number"]) for r in result["tree"]) <= 3


def test_the_book_reports_its_own_depth(tmp_path):
    assert LocalOpeningDatabase(book(tmp_path, 7)).max_ply == 14
    # a book whose filters say nothing must not be guessed at
    db = LocalOpeningDatabase(book(tmp_path, 7))
    db._meta["filters"] = "speeds=blitz"        # noqa: SLF001 - the point of the test
    assert db.max_ply is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_a_book_can_be_rebuilt_over_itself(tmp_path):
    """Interning must not make the next build impossible.

    `intern_positions` leaves `moves` as a view, and SQLite will not insert into
    one. Building over an existing book is ordinary — deepening it, adding a
    month — so the builder has to undo the interned shape before it writes, and
    restore it afterwards. Without that the second build dies with "cannot
    modify moves because it is a view".
    """
    from build_local_db import build  # noqa: PLC0415

    path = str(tmp_path / "rebuilt.sqlite")
    for _ in range(2):
        build(find_pgn_files(PGN_DIR), path, max_moves=6, speeds=None,
              min_move_games=1, offline_eco=True)

    db = LocalOpeningDatabase(path)
    assert db.max_ply == 12
    con = sqlite3.connect(path)
    kinds = dict(con.execute("SELECT name, type FROM sqlite_master "
                             "WHERE name IN ('moves', 'moves_i', 'positions')"))
    # The rebuild has to leave the book interned, not just writable.
    assert kinds == {"moves": "view", "moves_i": "table", "positions": "table"}
    rows = con.execute("SELECT count(*) FROM moves").fetchone()[0]
    # Rebuilding must not double the counts: the second pass starts from empty.
    assert rows == con.execute("SELECT count(*) FROM moves_i").fetchone()[0]
    con.close()
