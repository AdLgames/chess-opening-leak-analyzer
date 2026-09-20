#!/usr/bin/env python3
"""Build the precomputed evaluation store from the Lichess evaluations dataset.

    # download once from https://database.lichess.org/ (the "evals" file, CC0)
    python tools/ingest_evals.py --evals lichess_db_eval.jsonl.zst

The file is very large and is never stored: it is streamed, and only positions already in
the opening book are kept, which is what brings it down to something worth shipping. Same
shape as `build_local_db.py`, which streams the games dump the same way.

Reading `.zst` needs `zstandard` (pip install zstandard) or the `zstd` command on PATH;
plain `.jsonl` and `.jsonl.gz` need neither.
"""
from __future__ import annotations

import argparse
import gzip
import os
import sqlite3
import subprocess
import sys
from typing import Iterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chessopening.evalstore import DEFAULT_EVALS, ingest  # noqa: E402
from chessopening.localdb import DEFAULT_DB  # noqa: E402


def stream(path: str) -> Iterator[str]:
    """Lines from .jsonl, .jsonl.gz or .jsonl.zst without unpacking to disk."""
    if path.endswith(".zst"):
        try:
            import zstandard  # noqa: PLC0415 - optional, only for this format

            with open(path, "rb") as raw:
                reader = zstandard.ZstdDecompressor().stream_reader(raw)
                for line in io_text(reader):
                    yield line
            return
        except ImportError:
            pass
        # Fall back to the zstd binary, which is usually already around.
        proc = subprocess.Popen(["zstd", "-dc", path], stdout=subprocess.PIPE, text=True)
        assert proc.stdout is not None
        yield from proc.stdout
        proc.wait()
        return
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            yield from fh
        return
    with open(path, encoding="utf-8") as fh:
        yield from fh


def io_text(reader) -> Iterator[str]:
    import io  # noqa: PLC0415

    yield from io.TextIOWrapper(reader, encoding="utf-8")


def book_positions(db_path: str) -> set[str]:
    """Every position the opening book knows, so the ingest can drop everything else."""
    con = sqlite3.connect(db_path)
    try:
        return {row[0] for row in con.execute("SELECT DISTINCT pos FROM moves")}
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evals", required=True, help="lichess_db_eval.jsonl[.zst|.gz]")
    ap.add_argument("--book", default=DEFAULT_DB, help="opening book to filter against")
    ap.add_argument("--out", default=DEFAULT_EVALS)
    ap.add_argument("--max-pvs", type=int, default=3)
    ap.add_argument("--pov", choices=["auto", "white", "mover"], default="auto",
                    help="source sign convention; 'auto' works it out from the data")
    ap.add_argument("--all-positions", action="store_true",
                    help="keep every position, not only those in the book (much larger)")
    args = ap.parse_args()

    wanted = None
    if not args.all_positions:
        if not os.path.exists(args.book):
            print(f"No opening book at {args.book} — pass --all-positions to skip filtering",
                  file=sys.stderr)
            return 2
        wanted = book_positions(args.book)
        print(f"Filtering against {len(wanted):,} book positions")

    stats = ingest(stream(args.evals), args.out, wanted=wanted, pov=args.pov,
                   max_pvs=args.max_pvs)
    size_mb = os.path.getsize(args.out) / 1e6 if os.path.exists(args.out) else 0
    print(f"Read {stats['seen']:,} records, kept {stats['kept']:,}, "
          f"skipped {stats['skipped']:,} -> {args.out} ({size_mb:.1f} MB)")
    if wanted:
        print(f"Book coverage: {stats['kept']:,} of {len(wanted):,} positions "
              f"({100 * stats['kept'] / max(1, len(wanted)):.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
