#!/usr/bin/env python3
"""Check an opening book before it is committed.

Building the book takes hours on a machine that can reach database.lichess.org, so
the answer to "did that work?" should not be "deploy it and see". This reports what
a book actually contains and fails loudly on the things that would be silently
wrong in production:

  * no rating bands, so every player is compared against everyone at once
  * shallower than the analyser's window, so following the book past the fixed
    cutoff follows nothing
  * an empty or truncated file that still opens as valid SQLite

    python tools/check_book.py chessopening/data/openings.sqlite --expect-moves 20
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chessopening.bands import ALL, BANDS  # noqa: E402


def check(path: str, expect_moves: int | None, max_mb: float | None = None) -> int:
    if not os.path.isfile(path):
        print(f"FAIL  no such file: {path}")
        return 1
    size_mb = os.path.getsize(path) / 1e6
    with open(path, "rb") as fh:
        if fh.read(16) != b"SQLite format 3\x00":
            print(f"FAIL  {path} is not a SQLite database "
                  f"({'a Git LFS pointer?' if size_mb < 0.001 else f'{size_mb:.1f} MB'})")
            return 1

    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    problems: list[str] = []
    try:
        meta = {r[0]: r[1] for r in con.execute("SELECT key, value FROM meta")}
        rows = con.execute("SELECT COUNT(*) FROM moves").fetchone()[0]
        positions = con.execute("SELECT COUNT(DISTINCT pos) FROM moves").fetchone()[0]
        named = con.execute("SELECT COUNT(*) FROM openings").fetchone()[0]
        columns = [r[1] for r in con.execute("PRAGMA table_info(moves)")]
    except sqlite3.DatabaseError as exc:
        print(f"FAIL  {path} does not look like an opening book: {exc}")
        return 1

    print(f"file        {path}  ({size_mb:.1f} MB)")
    print(f"games       {meta.get('games', '?')}")
    print(f"source      {meta.get('source', '?')}")
    print(f"filters     {meta.get('filters', '?')}")
    print(f"built       {meta.get('built_at', '?')}")
    print(f"content     {positions} positions, {rows} move rows, {named} named openings")

    if not rows or not positions:
        problems.append("the book is empty")

    # Depth: the builder records it in the filters string.
    match = re.search(r"max_moves=(\d+)", meta.get("filters", "") or "")
    depth = int(match.group(1)) if match else None
    print(f"depth       {'move ' + str(depth) if depth else 'not recorded'}")
    if depth is None:
        problems.append("the filters string does not record max_moves, so the analyser "
                        "cannot tell how deep the book goes")
    elif expect_moves is not None and depth < expect_moves:
        problems.append(f"built to move {depth}, but move {expect_moves} was expected — "
                        "decisions past that cannot be checked against theory")

    # Bands: the whole point of the rating-band comparison.
    if "band" not in columns:
        problems.append("no band column: every player will be compared against all "
                        "ratings at once. Rebuild with a version of build_local_db "
                        "that writes bands.")
    else:
        present = {r[0] for r in con.execute("SELECT DISTINCT band FROM moves")}
        known = {name for name, _lo, _hi in BANDS}
        print(f"bands       {', '.join(sorted(present)) or 'none'}")
        if ALL not in present:
            problems.append(f"no '{ALL}' rows: a player outside every band would get "
                            "no baseline at all")
        if not (present & known):
            problems.append("only 'all' rows: nothing to compare a rated player against")
    con.close()

    if max_mb is not None and size_mb > max_mb:
        problems.append(
            f"{size_mb:.1f} MB exceeds the {max_mb:.0f} MB budget. The deployment bundles "
            "this file with the engine and the Python dependencies under a fixed total, so "
            "an oversized book does not fail here — the deployed function fails to start "
            "at all, on every request. Raise --min-move-games and build again.")

    if problems:
        print()
        for p in problems:
            print(f"FAIL  {p}")
        return 1
    print("\nOK    this book is usable")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?",
                    default=os.path.join(os.path.dirname(os.path.dirname(
                        os.path.abspath(__file__))), "chessopening", "data",
                        "openings.sqlite"))
    ap.add_argument("--expect-moves", type=int, default=None,
                    help="fail if the book is shallower than this many full moves")
    ap.add_argument("--max-mb", type=float, default=None,
                    help="fail if the book is larger than this, before it reaches a deploy")
    args = ap.parse_args()
    return check(args.path, args.expect_moves, args.max_mb)


if __name__ == "__main__":
    raise SystemExit(main())
