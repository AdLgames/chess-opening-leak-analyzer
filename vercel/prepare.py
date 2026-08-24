#!/usr/bin/env python3
"""Assemble this folder into a deployable Vercel bundle.

Run as the Vercel build command (or by hand before `vercel deploy`). Nothing it
produces is committed — see ../.gitignore.

Steps
  1. copy the analyzer package and the demo PGNs in from ../chess_opening_analyzer
  2. copy the dashboard front-end in from ../chess-dashboard/public
  3. make sure chessopening/data/openings.sqlite is real content, not a Git LFS
     pointer (Vercel's git clone does not fetch LFS objects, so it is pulled from
     media.githubusercontent.com, which serves LFS files directly)
  4. download the Stockfish build that runs on the function's CPU

Override the database source with LEAKLAB_DB_URL, or the repo it comes from with
LEAKLAB_REPO and LEAKLAB_REF.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ANALYZER = os.path.join(REPO, "chess_opening_analyzer")
DASHBOARD = os.path.join(REPO, "chess-dashboard")

DB_REL = os.path.join("chessopening", "data", "openings.sqlite")
GH_REPO = os.environ.get("LEAKLAB_REPO", "AdLgames/chess-opening-leak-analyzer")
GH_REF = os.environ.get("LEAKLAB_REF", "main")
DB_URL = os.environ.get(
    "LEAKLAB_DB_URL",
    f"https://media.githubusercontent.com/media/{GH_REPO}/{GH_REF}/"
    f"chess_opening_analyzer/chessopening/data/openings.sqlite",
)
LFS_MAGIC = b"version https://git-lfs.github.com/spec/"
ENGINE_BUILD = os.environ.get("LEAKLAB_ENGINE_BUILD", "sse41-popcnt")


def say(*parts: object) -> None:
    print("[prepare]", *parts, flush=True)


def copy_tree(src: str, dst: str, skip: tuple[str, ...] = ()) -> None:
    if not os.path.isdir(src):
        raise SystemExit(f"missing {src} — run this from a full checkout of the repo")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", *skip))
    say(f"copied {os.path.relpath(src, REPO)} -> {os.path.relpath(dst, HERE)}")


def is_pointer(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(len(LFS_MAGIC)) == LFS_MAGIC
    except OSError:
        return True


def ensure_database() -> None:
    path = os.path.join(HERE, DB_REL)
    if os.path.isfile(path) and not is_pointer(path):
        say(f"database present ({os.path.getsize(path) / 1e6:.1f} MB)")
        return
    say(f"database is a pointer or missing, downloading from {DB_URL}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with urllib.request.urlopen(DB_URL, timeout=180) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out)
    if is_pointer(tmp):
        os.remove(tmp)
        raise SystemExit("the download was another LFS pointer — check LEAKLAB_DB_URL")
    os.replace(tmp, path)
    say(f"database ready ({os.path.getsize(path) / 1e6:.1f} MB)")


def ensure_engine() -> None:
    dest = os.path.join(HERE, "engine")
    installer = os.path.join(ANALYZER, "tools", "install_stockfish.py")
    cmd = [sys.executable, installer, "--dest", dest, "--build", ENGINE_BUILD]
    say(" ".join(cmd[1:]))
    subprocess.run(cmd, check=True)


def main() -> int:
    copy_tree(os.path.join(ANALYZER, "chessopening"), os.path.join(HERE, "chessopening"),
              skip=("bin",))
    copy_tree(os.path.join(ANALYZER, "sample_pgns"), os.path.join(HERE, "sample_pgns"))
    copy_tree(os.path.join(DASHBOARD, "public"), os.path.join(HERE, "public"))
    ensure_database()
    ensure_engine()
    say("bundle ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
