"""Download a Stockfish binary into the package so the app ships with its own engine.

    python tools/install_stockfish.py            # auto-detect platform
    python tools/install_stockfish.py --version sf_17.1 --build sse41-popcnt

Binary lands in chessopening/bin/ and is picked up automatically by find_engine().
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

REL = "https://github.com/official-stockfish/Stockfish/releases/download"
PKG_BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chessopening", "bin")


def detect_asset(build: str | None = None) -> tuple[str, str]:
    """Return (asset_filename, binary_name_inside_archive_hint)."""
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    if sysname == "darwin":
        arch = "m1-apple-silicon" if machine in ("arm64", "aarch64") else "x86-64-avx2"
        return f"stockfish-macos-{arch}.tar", "stockfish"
    if sysname == "windows":
        return f"stockfish-windows-x86-64-{build or 'avx2'}.zip", "stockfish.exe"
    if machine in ("arm64", "aarch64"):
        return "stockfish-android-armv8.tar", "stockfish"
    return f"stockfish-ubuntu-x86-64-{build or 'avx2'}.tar", "stockfish"


def install(version: str = "sf_17.1", build: str | None = None, dest_dir: str = PKG_BIN) -> str:
    asset, binname = detect_asset(build)
    url = f"{REL}/{version}/{asset}"
    os.makedirs(dest_dir, exist_ok=True)
    print(f"Downloading {url}")
    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, asset)
        with urllib.request.urlopen(url, timeout=180) as resp, open(archive, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        extract_dir = os.path.join(tmp, "x")
        if asset.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(archive) as tf:
                tf.extractall(extract_dir)
        found = None
        for root, _dirs, files in os.walk(extract_dir):
            for f in files:
                low = f.lower()
                if low.startswith("stockfish") and not low.endswith((".txt", ".md", ".cff", ".nnue")):
                    p = os.path.join(root, f)
                    if os.path.isfile(p) and os.path.getsize(p) > 1_000_000:
                        found = p
                        break
            if found:
                break
        if not found:
            raise SystemExit(f"No Stockfish binary inside {asset}")
        target = os.path.join(dest_dir, binname)
        shutil.copy2(found, target)
    os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    out = subprocess.run([target], input="uci\nquit\n", capture_output=True, text=True, timeout=30).stdout
    idname = next((l for l in out.splitlines() if l.startswith("id name")), "?")
    print(f"Installed {target}\n{idname}")
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description="Install a bundled Stockfish binary")
    ap.add_argument("--version", default="sf_17.1", help="Stockfish release tag")
    ap.add_argument("--build", help="CPU build: avx2 (default), sse41-popcnt, bmi2, vnni512")
    ap.add_argument("--dest", default=PKG_BIN)
    args = ap.parse_args()
    try:
        install(args.version, args.build, args.dest)
    except Exception as exc:  # noqa: BLE001
        print(f"Install failed: {exc}\nFall back to: apt install stockfish / brew install stockfish",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
