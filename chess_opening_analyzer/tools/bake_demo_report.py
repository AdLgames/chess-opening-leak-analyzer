#!/usr/bin/env python3
"""Pre-compute the demo report so the hosted deployment can answer it instantly.

    python chess_opening_analyzer/tools/bake_demo_report.py

Writes `chess-dashboard/demo_report.json` (the local server reads it) and, when
`vercel/` is being deployed, copy the same file to `vercel/demo_report.json` —
both backends look for it before running anything.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REPO = os.path.dirname(PKG)
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from chessopening.demo import build_demo_report  # noqa: E402

DEFAULT_SAMPLES = os.path.join(REPO, "chess-dashboard", "sample_pgns")
DEFAULT_OUT = os.path.join(REPO, "chess-dashboard", "demo_report.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", default=DEFAULT_SAMPLES, help="folder of sample PGNs")
    ap.add_argument("--out", default=DEFAULT_OUT, help="where to write the payload")
    ap.add_argument("--also", action="append", default=[], help="extra copies to write")
    args = ap.parse_args()

    work = tempfile.mkdtemp(prefix="leaklab-demo-")
    try:
        payload = build_demo_report(args.samples, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    for extra in args.also:
        shutil.copyfile(args.out, extra)
    print(f"{len(payload['rows'])} leaks over {payload['summary']['games']} games -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
