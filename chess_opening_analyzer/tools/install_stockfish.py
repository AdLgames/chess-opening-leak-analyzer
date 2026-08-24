"""Download a Stockfish binary into the package so the app ships with its own engine.

    python tools/install_stockfish.py                  # auto-detect platform, skip if present
    python tools/install_stockfish.py --force          # reinstall even if a working engine exists
    python tools/install_stockfish.py --check          # report what is installed, download nothing
    python tools/install_stockfish.py --version sf_17.1 --build sse41-popcnt

The binary lands in chessopening/bin/ and is picked up automatically by find_engine().
That directory is git-ignored: the engine is fetched per machine rather than committed,
so the CPU build always matches the host.
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
import urllib.error
import urllib.request
import zipfile

REL = "https://github.com/official-stockfish/Stockfish/releases/download"
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_BIN = os.path.join(PKG_ROOT, "chessopening", "bin")

#: tried in order on x86-64 — newest instruction set first, plain build last
X86_BUILDS = ("avx2", "sse41-popcnt")


def binary_name() -> str:
    return "stockfish.exe" if platform.system().lower() == "windows" else "stockfish"


def candidate_assets(build: str | None = None) -> list[str]:
    """Release asset names to try, most specific first."""
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")

    if sysname == "darwin":
        return [f"stockfish-macos-{'m1-apple-silicon' if arm else 'x86-64-avx2'}.tar"]
    if sysname == "windows":
        builds = (build,) if build else X86_BUILDS
        return [f"stockfish-windows-x86-64-{b}.zip" for b in builds]
    if arm:
        return ["stockfish-android-armv8.tar"]
    builds = (build,) if build else X86_BUILDS
    return [f"stockfish-ubuntu-x86-64-{b}.tar" for b in builds]


def engine_id(path: str) -> str | None:
    """Run the binary and return its `id name` line, or None if it will not run here."""
    try:
        out = subprocess.run([path], input="uci\nquit\n", capture_output=True,
                             text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return next((l.strip() for l in out.splitlines() if l.startswith("id name")), None)


def installed(dest_dir: str = PKG_BIN) -> tuple[str, str] | None:
    """(path, id_name) of a working engine already in `dest_dir`, else None."""
    path = os.path.join(dest_dir, binary_name())
    if not os.path.isfile(path):
        return None
    idname = engine_id(path)
    return (path, idname) if idname else None


def _extract_binary(archive: str, into: str) -> str:
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(into)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(into)
    for root, _dirs, files in os.walk(into):
        for f in sorted(files):
            low = f.lower()
            if low.startswith("stockfish") and not low.endswith((".txt", ".md", ".cff", ".nnue")):
                p = os.path.join(root, f)
                if os.path.isfile(p) and os.path.getsize(p) > 1_000_000:
                    return p
    raise RuntimeError(f"no Stockfish binary inside {os.path.basename(archive)}")


def install(version: str = "sf_17.1", build: str | None = None, dest_dir: str = PKG_BIN,
            force: bool = False, quiet: bool = False) -> str:
    """Fetch Stockfish into `dest_dir` and return its path.

    Existing working engines are kept unless `force`. Each candidate CPU build is
    downloaded and actually run before being accepted, so a machine without AVX2
    falls back to the SSE build instead of installing something that crashes.
    """
    def say(msg: str) -> None:
        if not quiet:
            print(msg)

    if not force:
        have = installed(dest_dir)
        if have:
            say(f"Already installed: {have[0]}\n{have[1]}  (use --force to reinstall)")
            return have[0]

    os.makedirs(dest_dir, exist_ok=True)
    target = os.path.join(dest_dir, binary_name())
    problems: list[str] = []

    for asset in candidate_assets(build):
        url = f"{REL}/{version}/{asset}"
        say(f"Downloading {url}")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                archive = os.path.join(tmp, asset)
                with urllib.request.urlopen(url, timeout=180) as resp, open(archive, "wb") as fh:
                    shutil.copyfileobj(resp, fh)
                found = _extract_binary(archive, os.path.join(tmp, "x"))
                shutil.copy2(found, target)
        except (urllib.error.URLError, OSError, RuntimeError, tarfile.TarError,
                zipfile.BadZipFile) as exc:
            problems.append(f"{asset}: {exc}")
            continue

        os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        idname = engine_id(target)
        if idname:
            say(f"Installed {target}\n{idname}")
            return target
        problems.append(f"{asset}: downloaded but would not run on this CPU")
        os.remove(target)

    raise RuntimeError("could not install Stockfish:\n  " + "\n  ".join(problems))


def main() -> int:
    ap = argparse.ArgumentParser(description="Install a bundled Stockfish binary")
    ap.add_argument("--version", default="sf_17.1", help="Stockfish release tag")
    ap.add_argument("--build", help="CPU build: avx2, sse41-popcnt, bmi2, vnni512 (default: try avx2 then sse41-popcnt)")
    ap.add_argument("--dest", default=PKG_BIN, help="install directory")
    ap.add_argument("--force", action="store_true", help="reinstall even if an engine is present")
    ap.add_argument("--check", action="store_true", help="report the installed engine and exit")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.check:
        have = installed(args.dest)
        if have:
            print(f"{have[1]}\npath: {have[0]}")
            return 0
        print(f"No working engine in {args.dest}. Run: python tools/install_stockfish.py")
        return 1

    try:
        install(args.version, args.build, args.dest, force=args.force, quiet=args.quiet)
    except Exception as exc:  # noqa: BLE001
        print(f"Install failed: {exc}\n"
              "Alternatives: apt install stockfish / brew install stockfish / winget install stockfish,\n"
              "then pass --engine /path/to/stockfish or set STOCKFISH_PATH.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
