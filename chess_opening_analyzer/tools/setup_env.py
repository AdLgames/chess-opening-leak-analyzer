"""One command to get a fresh clone ready: dependencies, engine, opening book, smoke test.

    python tools/setup_env.py                 # install everything that is missing
    python tools/setup_env.py --no-deps       # skip pip, just engine + checks
    python tools/setup_env.py --dashboard     # also install the dashboard's extras

Safe to re-run: each step is skipped when it is already satisfied.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(PKG_ROOT)
sys.path.insert(0, PKG_ROOT)

DASHBOARD_EXTRAS = ["fastapi", "uvicorn", "python-multipart"]


def is_lfs_pointer(path: str) -> bool:
    """True when the file is an unfetched Git LFS pointer instead of real content."""
    try:
        with open(path, "rb") as fh:
            return fh.read(48).startswith(b"version https://git-lfs.github.com/spec/")
    except OSError:
        return False


def step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}")


def pip_install(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *args], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare a clone for use")
    ap.add_argument("--no-deps", action="store_true", help="skip pip install")
    ap.add_argument("--dashboard", action="store_true", help="also install fastapi/uvicorn extras")
    ap.add_argument("--force-engine", action="store_true", help="reinstall Stockfish")
    args = ap.parse_args()

    total = 4
    ok = True

    step(1, total, "Python dependencies")
    if args.no_deps:
        print("skipped")
    else:
        pip_install(["-r", os.path.join(PKG_ROOT, "requirements.txt")])
        if args.dashboard:
            pip_install(DASHBOARD_EXTRAS)
        print("done")

    step(2, total, "Stockfish engine")
    from tools.install_stockfish import install, installed  # noqa: PLC0415

    try:
        path = install(force=args.force_engine)
        print(f"engine ready: {path}")
    except Exception as exc:  # noqa: BLE001
        have = installed()
        if have:
            print(f"kept existing engine: {have[0]}")
        else:
            ok = False
            print(f"engine unavailable: {exc}\n"
                  "The analyzer still runs with --no-engine (statistics only).")

    step(3, total, "Opening database")
    from chessopening.localdb import DEFAULT_DB, LocalOpeningDatabase  # noqa: PLC0415

    if os.path.isfile(DEFAULT_DB) and is_lfs_pointer(DEFAULT_DB):
        ok = False
        print(f"{DEFAULT_DB} is still a Git LFS pointer, not the real database.\n"
              "Fetch it with: git lfs install && git lfs pull\n"
              "Or build your own: python tools/build_local_db.py --help")
    elif os.path.isfile(DEFAULT_DB):
        db = LocalOpeningDatabase(DEFAULT_DB)
        try:
            print(f"{DEFAULT_DB}\n{db.description}")
        finally:
            db.close()
    else:
        ok = False
        print(f"missing {DEFAULT_DB}\n"
              "Git LFS not pulled? Run: git lfs install && git lfs pull\n"
              "Or build your own: python tools/build_local_db.py --help")

    step(4, total, "Smoke test")
    if not os.path.isdir(os.path.join(PKG_ROOT, "sample_pgns")):
        subprocess.run([sys.executable, os.path.join(HERE, "make_sample_pgns.py")], check=True)
    cmd = [sys.executable, "-m", "chessopening", "--pgn-dir", "sample_pgns", "--db", "local",
           "--min-db-games", "20", "--depth", "8", "--max-moves", "8", "--out-dir", "out"]
    if not installed():
        cmd.append("--no-engine")
    res = subprocess.run(cmd, cwd=PKG_ROOT)
    if res.returncode == 0:
        print(f"\nWrote {os.path.join(PKG_ROOT, 'out', 'opening_leaks.csv')}")
    else:
        ok = False

    print("\nReady." if ok else "\nFinished with warnings above.")
    if args.dashboard:
        print("Start the dashboard:\n"
              f"  cd {os.path.join(REPO_ROOT, 'chess-dashboard')}\n"
              "  python api_server.py            # API on :8000\n"
              "  python -m http.server 8080 -d public")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
