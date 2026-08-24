"""Command line interface: python -m chessopening --pgn-dir ... --player ..."""
from __future__ import annotations

import argparse
import sys

from .analyze import analyze
from .engine import bundled_engine
from .ingest import DEFAULT_CACHE, FetchOptions, IngestError, fetch_games, speeds_from_csv
from .localdb import DEFAULT_DB
from .pgn_loader import detect_main_player, find_pgn_files


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chessopening",
        description="Analyze a folder of PGNs: Lichess Opening Explorer cross-reference + "
                    "Stockfish evaluation-drop detection in the opening, exported as CSV.",
    )
    src = p.add_argument_group("where the games come from")
    src.add_argument("--pgn-dir", help="Folder (searched recursively) or single .pgn file")
    src.add_argument("--user", help="Fetch this player's games instead of reading files")
    src.add_argument("--provider", choices=["lichess", "chesscom"], default="chesscom",
                     help="Which site to fetch --user from (default chesscom)")
    src.add_argument("--max-games", type=int, default=200, help="Cap on fetched games")
    src.add_argument("--time-classes", default="blitz,rapid,classical",
                     help="Comma separated: bullet,blitz,rapid,classical,daily")
    src.add_argument("--include-unrated", action="store_true", help="Keep casual games too")
    src.add_argument("--since", help="Earliest game date, YYYY-MM-DD")
    src.add_argument("--until", help="Latest game date, YYYY-MM-DD")
    src.add_argument("--lichess-token", help="Lichess personal API token, if the export needs one")
    src.add_argument("--archive-cache", default=DEFAULT_CACHE, help="Where fetched PGNs are cached")
    src.add_argument("--refresh", action="store_true", help="Refetch months already cached")
    p.add_argument("--player", help="Player name as it appears in PGN headers (auto-detected if omitted)")
    p.add_argument("--out-dir", default="out", help="Where CSVs and caches are written")
    p.add_argument("--color", choices=["white", "black", "both"], default="both")
    p.add_argument("--max-moves", type=int, default=15, help="Opening depth in full moves (default 15)")
    p.add_argument("--min-games", type=int, default=3, help="Only judge decisions repeated this often")
    p.add_argument("--min-ply", type=int, default=2,
                   help="Ignore decisions before this ply (default 2: skips the first move choice)")
    p.add_argument("--eval-drop", type=float, default=0.8, help="Eval drop in pawns that counts as a mistake")
    p.add_argument("--score-gap", type=float, default=0.06,
                   help="Win-rate shortfall vs database (0.06 = 6 score points) that counts as a decline")
    # engine
    p.add_argument("--engine", help="Path to the Stockfish binary (else $STOCKFISH_PATH or PATH)")
    p.add_argument("--depth", type=int, default=18)
    p.add_argument("--movetime", type=int, help="Milliseconds per position instead of fixed depth")
    p.add_argument("--multipv", type=int, default=3, help="How many engine alternatives to report")
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--no-engine", action="store_true", help="Skip Stockfish, database comparison only")
    # explorer
    p.add_argument("--db", choices=["local", "lichess", "masters"], default="local",
                   help="local = bundled SQLite database (no network); lichess/masters = Explorer API")
    p.add_argument("--local-db", default=DEFAULT_DB, help="Path to the SQLite opening database")
    p.add_argument("--min-db-games", type=int, default=20,
                   help="Ignore local-database positions with fewer games than this")
    p.add_argument("--speeds", default="blitz,rapid,classical")
    p.add_argument("--ratings", default="1600,1800,2000",
                   help="Lichess rating buckets: 0,1000,1200,1400,1600,1800,2000,2200,2500")
    p.add_argument("--offline", action="store_true", help="Use only cached Explorer responses")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.pgn_dir and not args.user:
        parser.error("pass --pgn-dir (local files) or --user (fetch from a site)")
    if args.pgn_dir and args.user:
        parser.error("--pgn-dir and --user are alternatives, not a pair")

    pgn_dir = args.pgn_dir
    player = args.player
    if args.user:
        try:
            fetched = fetch_games(
                FetchOptions(
                    provider=args.provider,
                    username=args.user,
                    max_games=args.max_games,
                    speeds=speeds_from_csv(args.time_classes),
                    rated_only=not args.include_unrated,
                    since=args.since,
                    until=args.until,
                    token=args.lichess_token,
                    cache_dir=args.archive_cache,
                    refresh=args.refresh,
                ),
                progress=print,
            )
        except IngestError as exc:
            print(f"Could not fetch games: {exc}", file=sys.stderr)
            if exc.hint:
                print(exc.hint, file=sys.stderr)
            if exc.download_url:
                print(f"Manual export: {exc.download_url}", file=sys.stderr)
            return 3
        pgn_dir = fetched.pgn_dir
        player = player or fetched.username
    if not player:
        player = detect_main_player(find_pgn_files(pgn_dir))
        if not player:
            print("Could not auto-detect a player; pass --player.", file=sys.stderr)
            return 2
        print(f"Auto-detected player: {player}")
    if not args.no_engine and not args.engine and bundled_engine():
        print(f"Using bundled engine: {bundled_engine()}")
    result = analyze(
        pgn_dir=pgn_dir,
        player=player,
        out_dir=args.out_dir,
        engine_path=args.engine,
        depth=args.depth,
        movetime_ms=args.movetime,
        multipv=args.multipv,
        threads=args.threads,
        max_moves=args.max_moves,
        color=args.color,
        min_games=args.min_games,
        min_ply=args.min_ply,
        eval_drop_threshold=args.eval_drop,
        score_gap_threshold=args.score_gap,
        db=args.db,
        local_db_path=args.local_db,
        min_db_games=args.min_db_games,
        speeds=args.speeds,
        ratings=args.ratings,
        offline=args.offline,
        no_engine=args.no_engine,
    )
    print(
        f"\nDone: {result['games']} games, {result['repeated']} repeated decisions analysed, "
        f"{result['rows']} leaks reported."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
