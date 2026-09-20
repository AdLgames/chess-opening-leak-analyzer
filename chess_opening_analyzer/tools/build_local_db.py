"""Build the offline opening database (move statistics + ECO names) used by --db local.

Sources
  * Lichess monthly dumps from https://database.lichess.org (CC0), streamed and filtered
  * ECO names from https://github.com/lichess-org/chess-openings (CC0)
  * or any local PGN files/folders you already have

Examples
  python tools/build_local_db.py --months 2013-01 --max-moves 15 --speeds blitz,rapid,classical
  python tools/build_local_db.py --months 2014-07 2014-08 --min-elo 1600 --max-elo 2000
  python tools/build_local_db.py --pgn ~/my_corpus --out chessopening/data/openings.sqlite
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

import chess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chessopening.bands import ALL, band_for  # noqa: E402
from chessopening.localdb import DEFAULT_DB, connect  # noqa: E402
from chessopening.pgn_loader import find_pgn_files  # noqa: E402

LICHESS_DUMP = "https://database.lichess.org/standard/lichess_db_standard_rated_{month}.pgn.zst"
ECO_TSVS = [f"https://raw.githubusercontent.com/lichess-org/chess-openings/master/{c}.tsv"
            for c in "abcde"]
ECO_LOCAL = os.path.join(os.path.dirname(DEFAULT_DB), "eco.tsv")

HEADER_RE = re.compile(r'^\[(\w+)\s+"(.*)"\]$')
COMMENT_RE = re.compile(r"\{[^}]*\}|;[^\n]*|\$\d+|\([^()]*\)")
TOKEN_RE = re.compile(r"[A-Za-z][\w+#=\-]*")
RESULTS = {"1-0": 0, "0-1": 2, "1/2-1/2": 1}


# ----------------------------------------------------------------- streaming
def stream_lines(path_or_url: str):
    """Yield text lines from a .pgn, .pgn.zst or .pgn.gz file, local or over HTTP."""
    if path_or_url.startswith(("http://", "https://")):
        raw = urllib.request.urlopen(path_or_url, timeout=300)
    else:
        raw = open(path_or_url, "rb")
    try:
        if path_or_url.endswith(".zst"):
            import zstandard  # pip install zstandard

            reader = zstandard.ZstdDecompressor().stream_reader(raw)
            stream = io.TextIOWrapper(io.BufferedReader(reader, 1 << 20), encoding="utf-8", errors="replace")
        elif path_or_url.endswith(".gz"):
            import gzip

            stream = io.TextIOWrapper(gzip.GzipFile(fileobj=raw), encoding="utf-8", errors="replace")
        else:
            stream = io.TextIOWrapper(io.BufferedReader(raw, 1 << 20), encoding="utf-8", errors="replace")
        yield from stream
    finally:
        raw.close()


def iter_games(path_or_url: str):
    """Yield (headers dict, movetext str) pairs without building full game trees."""
    headers: dict[str, str] = {}
    moves: list[str] = []
    in_moves = False
    for line in stream_lines(path_or_url):
        line = line.strip()
        if line.startswith("["):
            if in_moves:
                yield headers, " ".join(moves)
                headers, moves, in_moves = {}, [], False
            m = HEADER_RE.match(line)
            if m:
                headers[m.group(1)] = m.group(2)
        elif line:
            in_moves = True
            moves.append(line)
    if headers and moves:
        yield headers, " ".join(moves)


# ----------------------------------------------------------------- filtering
def speed_of(headers: dict[str, str]) -> str:
    ev = headers.get("Event", "").lower()
    for s in ("ultrabullet", "bullet", "blitz", "rapid", "classical", "correspondence"):
        if s in ev:
            return s
    tc = headers.get("TimeControl", "")
    if "+" in tc:
        try:
            base, inc = (int(x) for x in tc.split("+"))
        except ValueError:
            return "unknown"
        est = base + 40 * inc
        if est < 30:
            return "ultrabullet"
        if est < 180:
            return "bullet"
        if est < 480:
            return "blitz"
        if est < 1500:
            return "rapid"
        return "classical"
    return "unknown"


def avg_elo(headers: dict[str, str]) -> int | None:
    try:
        return (int(headers["WhiteElo"]) + int(headers["BlackElo"])) // 2
    except (KeyError, ValueError):
        return None


# ----------------------------------------------------------------- ECO names
def load_eco_rows(offline: bool) -> list[tuple[str, str, str]]:
    if os.path.exists(ECO_LOCAL):
        with open(ECO_LOCAL, encoding="utf-8") as fh:
            text = fh.read()
    elif offline:
        return []
    else:
        chunks = []
        for url in ECO_TSVS:
            print(f"  fetching {url}")
            with urllib.request.urlopen(url, timeout=120) as resp:
                chunks.append(resp.read().decode("utf-8"))
        text = "\n".join(chunks)
        os.makedirs(os.path.dirname(ECO_LOCAL), exist_ok=True)
        with open(ECO_LOCAL, "w", encoding="utf-8") as fh:
            fh.write(text)
    rows = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or parts[0] == "eco":
            continue
        rows.append((parts[0], parts[1], parts[2]))
    return rows


def write_openings(con, offline: bool) -> int:
    rows = load_eco_rows(offline)
    out = []
    for eco, name, pgn in rows:
        board = chess.Board()
        try:
            for tok in TOKEN_RE.findall(re.sub(r"\d+\.(\.\.)?", " ", pgn)):
                board.push_san(tok)
        except (ValueError, AssertionError):
            continue
        out.append((board.epd(), eco, name))
    con.executemany("INSERT OR REPLACE INTO openings (pos, eco, name) VALUES (?,?,?)", out)
    con.commit()
    return len(out)


# ----------------------------------------------------------------- main build
def build(
    sources: list[str],
    out_path: str,
    max_moves: int = 15,
    speeds: set[str] | None = None,
    min_elo: int = 0,
    max_elo: int = 4000,
    max_games: int | None = None,
    min_move_games: int = 2,
    offline_eco: bool = False,
) -> dict:
    con = connect(out_path, create=True)
    print(f"Writing {out_path}")
    print("Importing ECO opening names...")
    named = write_openings(con, offline_eco)
    print(f"  {named} named opening lines")

    # Keyed by (position, move, band). Every game is counted twice: once into its own
    # rating band and once into "all", so a book can answer both "how does everybody do
    # here" and "how do players like me do here" without a second pass or a join.
    counts: dict[tuple[str, str, str], list] = defaultdict(lambda: [0, 0, 0, "", 0])
    kept = skipped = 0
    max_ply = max_moves * 2
    t0 = time.time()

    def flush() -> None:
        con.executemany(
            "INSERT INTO moves (pos, uci, band, san, white, draws, black, rating_sum) "
            "VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(pos, uci, band) DO UPDATE SET white = white + excluded.white, "
            "draws = draws + excluded.draws, black = black + excluded.black, "
            "rating_sum = rating_sum + excluded.rating_sum",
            [(pos, uci, band, v[3], v[0], v[1], v[2], v[4])
             for (pos, uci, band), v in counts.items()],
        )
        con.commit()
        counts.clear()

    for src in sources:
        print(f"Reading {src}")
        for headers, movetext in iter_games(src):
            result = headers.get("Result", "*")
            if result not in RESULTS:
                skipped += 1
                continue
            if speeds and speed_of(headers) not in speeds:
                skipped += 1
                continue
            elo = avg_elo(headers)
            if elo is not None and not (min_elo <= elo <= max_elo):
                skipped += 1
                continue
            # A game with no rating in its headers still belongs in "all" — dropping it
            # would quietly bias the overall numbers toward rated play.
            band = band_for(elo)
            buckets = (ALL,) if band == ALL else (ALL, band)
            # only the opening matters, so never clean or tokenise the whole game
            cleaned = COMMENT_RE.sub(" ", movetext[: 40 + 12 * max_ply])
            board = chess.Board()
            idx = RESULTS[result]
            plies = 0
            for tok in TOKEN_RE.findall(re.sub(r"\d+\.(\.\.)?", " ", cleaned)):
                if plies >= max_ply or tok in ("eval", "clk"):
                    break
                try:
                    move = board.parse_san(tok)
                except (ValueError, AssertionError, IndexError):
                    break  # truncated tail or annotation junk: keep what we already counted
                for bucket in buckets:
                    rec = counts[(board.epd(), move.uci(), bucket)]
                    rec[idx] += 1
                    if not rec[3]:
                        rec[3] = tok
                    rec[4] += elo or 0
                board.push(move)
                plies += 1
            if plies == 0:
                skipped += 1
                continue
            kept += 1
            if kept % 20000 == 0:
                flush()
                rate = kept / max(1e-9, time.time() - t0)
                print(f"  {kept} games kept, {skipped} skipped ({rate:.0f} games/s)")
            if max_games and kept >= max_games:
                break
        if max_games and kept >= max_games:
            break
    flush()

    if min_move_games > 1:
        # Only ever thin the "all" rows on this rule. A band row is a subset of one, so a
        # threshold meant for the whole book would delete most of every band.
        con.execute("DELETE FROM moves WHERE band = ? AND (white + draws + black) < ?",
                    (ALL, min_move_games))
        con.execute("DELETE FROM moves WHERE band != ? AND NOT EXISTS ("
                    "  SELECT 1 FROM moves m2 WHERE m2.pos = moves.pos AND m2.uci = moves.uci"
                    "    AND m2.band = ?)", (ALL, ALL))
    con.execute("CREATE INDEX IF NOT EXISTS idx_moves_pos ON moves (pos, band)")
    filters = f"speeds={','.join(sorted(speeds)) if speeds else 'all'} elo={min_elo}-{max_elo} " \
              f"max_moves={max_moves}"
    con.executemany(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)",
        [("games", str(kept)), ("source", "; ".join(os.path.basename(s) for s in sources)),
         ("filters", filters), ("bands", "1"),
         ("built_at", time.strftime("%Y-%m-%d %H:%M:%S"))],
    )
    con.commit()
    rows = con.execute("SELECT COUNT(*) FROM moves").fetchone()[0]
    positions = con.execute("SELECT COUNT(DISTINCT pos) FROM moves").fetchone()[0]
    con.execute("VACUUM")
    con.close()
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"Done: {kept} games, {positions} positions, {rows} position-move rows, {size_mb:.1f} MB "
          f"in {time.time() - t0:.0f}s")
    return {"games": kept, "positions": positions, "rows": rows, "path": out_path}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the offline opening statistics database")
    ap.add_argument("--months", nargs="*", default=[],
                    help="Lichess dump months, e.g. 2013-01 2013-02 (streamed, not stored)")
    ap.add_argument("--pgn", nargs="*", default=[], help="Local PGN files or folders to ingest")
    ap.add_argument("--out", default=DEFAULT_DB)
    ap.add_argument("--max-moves", type=int, default=15)
    ap.add_argument("--speeds", default="blitz,rapid,classical")
    ap.add_argument("--min-elo", type=int, default=0)
    ap.add_argument("--max-elo", type=int, default=4000)
    ap.add_argument("--max-games", type=int, help="Stop after this many accepted games")
    ap.add_argument("--min-move-games", type=int, default=2,
                    help="Drop position-moves seen fewer times (keeps the file small)")
    ap.add_argument("--offline-eco", action="store_true", help="Use the vendored eco.tsv only")
    args = ap.parse_args()

    sources = [LICHESS_DUMP.format(month=m) for m in args.months]
    for p in args.pgn:
        sources.extend(find_pgn_files(p))
    if not sources:
        ap.error("give --months and/or --pgn")
    speeds = {s.strip().lower() for s in args.speeds.split(",") if s.strip()} or None
    build(sources, args.out, max_moves=args.max_moves, speeds=speeds, min_elo=args.min_elo,
          max_elo=args.max_elo, max_games=args.max_games, min_move_games=args.min_move_games,
          offline_eco=args.offline_eco)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
