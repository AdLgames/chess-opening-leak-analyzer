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
  4. generate one page per opening the book can describe (see
     ../chess_opening_analyzer/tools/build_opening_pages.py)
  5. download the Stockfish build that runs on the function's CPU

Override the database source with LEAKLAB_DB_URL, or the repo it comes from with
LEAKLAB_REPO and LEAKLAB_REF. Pointing LEAKLAB_DB_URL at a GitHub Release asset
is worth doing for a large book: Release downloads do not count against the
repository's Git LFS bandwidth quota, and every build fetches this file.
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


#: Where a downloaded book is kept between builds. It has to sit outside the
#: directory `copy_tree` wipes, or every build re-downloads it — which is what
#: was happening: Vercel's git clone does not fetch LFS objects, so the copied
#: file is always a pointer and the real one was always fetched again. At ~19 MB
#: a build that is wasteful; at three times that it threatens GitHub's LFS
#: bandwidth quota, and an exhausted quota answers 403, which fails the build.
DB_CACHE = os.path.join(HERE, ".dbcache", os.path.basename(DB_REL))


def ensure_database() -> None:
    path = os.path.join(HERE, DB_REL)
    if os.path.isfile(path) and not is_pointer(path):
        say(f"database present ({os.path.getsize(path) / 1e6:.1f} MB)")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.isfile(DB_CACHE) and not is_pointer(DB_CACHE):
        shutil.copyfile(DB_CACHE, path)
        say(f"database from the build cache ({os.path.getsize(path) / 1e6:.1f} MB, "
            "no download)")
        return

    say(f"database is a pointer or missing, downloading from {DB_URL}")
    tmp = path + ".part"
    with urllib.request.urlopen(DB_URL, timeout=180) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out)
    if is_pointer(tmp):
        os.remove(tmp)
        raise SystemExit("the download was another LFS pointer — check LEAKLAB_DB_URL")
    os.replace(tmp, path)
    try:
        os.makedirs(os.path.dirname(DB_CACHE), exist_ok=True)
        shutil.copyfile(path, DB_CACHE)
    except OSError:
        pass        # an uncacheable build is slow, not broken
    say(f"database ready ({os.path.getsize(path) / 1e6:.1f} MB)")


def copy_demo_report() -> None:
    """Take the baked demo payload along if one has been generated.

    Without it the first visitor to click the demo waits for a real engine pass;
    with it the function answers from the file. See tools/bake_demo_report.py.
    """
    src = os.path.join(DASHBOARD, "demo_report.json")
    if not os.path.isfile(src):
        say("no baked demo report — the first demo run will compute one")
        return
    shutil.copyfile(src, os.path.join(HERE, "demo_report.json"))
    say(f"baked demo report copied ({os.path.getsize(src) / 1e6:.1f} MB)")


def build_opening_pages() -> None:
    """Generate the per-opening pages into the bundle, from the book just fetched.

    Generated rather than committed: they are a pure function of the book, so a
    hundred and fifty files in the repository would be a copy of something we
    already have, going stale the moment the book is rebuilt.
    """
    out = os.path.join(HERE, "public")
    tool = os.path.join(ANALYZER, "tools", "build_opening_pages.py")
    db = os.path.join(HERE, DB_REL)
    cmd = [sys.executable, tool, "--db", db, "--out", out]
    say(" ".join(cmd[1:]))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    for line in (result.stdout or "").splitlines():
        say(" ", line)
    if result.returncode != 0:
        # A bundle without them is a working site with fewer pages, which beats
        # a deployment that does not happen.
        say(f"opening pages skipped ({result.stderr.strip().splitlines()[-1:] or 'no output'})")


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
    copy_demo_report()
    ensure_database()
    build_opening_pages()
    ensure_engine()
    say("bundle ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
