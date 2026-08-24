# Chess Opening Leak Analyzer

Point it at a folder of PGN files. It parses your games with `python-chess`, cross-references
every opening decision against an opening database (**bundled local SQLite** by default, or the
**Lichess Opening Explorer** API), re-checks the same positions with **Stockfish** (UCI, MultiPV),
and writes a CSV of the variations and FEN positions where your results keep sliding — plus the
engine's top alternatives for each miss.

Runs fully offline: the engine and the opening database both live inside the app.

## Install

```bash
pip install -r requirements.txt              # python-chess, zstandard
python tools/install_stockfish.py            # bundles Stockfish into chessopening/bin/
python tools/build_local_db.py --months 2013-01 2013-02 2013-03 \
    --speeds blitz,rapid,classical --min-elo 1500 --max-elo 2100
```

`install_stockfish.py` detects your OS/CPU, pulls the official release (Linux, macOS Intel/Apple
Silicon, Windows) and verifies it answers `uci`. Engine lookup order: `--engine` → bundled copy →
`$STOCKFISH_PATH` → `PATH`, so a system Stockfish still works if you skip the bundling step.

`build_local_db.py` streams public [Lichess monthly dumps](https://database.lichess.org) (CC0) —
nothing is stored on disk except the resulting database — filters by speed and rating, and folds
the first 15 moves of every game into position-move statistics. It also imports ECO/opening names
from [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings) (CC0) into
`chessopening/data/eco.tsv`. The shipped database is 19 MB: 157,625 blitz/rapid/classical games
rated 1500-2100 from 2013-01..03 → 49,327 positions / 80,000 position-move rows. Add months or
`--pgn <folder>` to deepen it; use `--min-elo/--max-elo` to match your own pool.

## Run

```bash
python -m chessopening --pgn-dir ~/lichess_export --player YourUsername      # offline, bundled db

python -m chessopening \
  --pgn-dir ~/lichess_export --player YourUsername \
  --db lichess --ratings 1600,1800,2000 --speeds blitz,rapid \
  --depth 18 --multipv 3 --max-moves 15 --min-games 3 --eval-drop 0.8 \
  --out-dir out
```

`--player` is auto-detected from the PGN headers when omitted. Both `.pgn` files and nested
folders work. Useful flags:

| Flag | Meaning |
|---|---|
| `--db local` | Default. Bundled SQLite database, no network |
| `--local-db PATH` | Use a different database file (e.g. one built from master games) |
| `--min-db-games 20` | Ignore local-database positions thinner than this |
| `--max-moves 15` | Opening window in full moves (default 15 → first 30 plies) |
| `--min-games 3` | Only judge decisions you have repeated at least this often |
| `--min-ply 2` | Ignore decisions before this ply (skips the bare first-move choice) |
| `--eval-drop 0.8` | Centipawn loss, in pawns, that counts as a significant drop |
| `--score-gap 0.06` | Win-rate shortfall vs the database that counts as a decline (6 score points) |
| `--color white\|black\|both` | Restrict the repertoire side |
| `--db lichess\|masters` | Use the online Explorer instead (public games or OTB masters) |
| `--ratings` / `--speeds` | Explorer filters — match your own pool for a fair baseline |
| `--movetime 300` | Fixed ms per position instead of fixed depth (faster on big archives) |
| `--offline` | Use only cached Explorer responses (no network) |
| `--no-engine` | Database comparison only, skip Stockfish |

Explorer responses and engine evaluations are cached under `<out-dir>/.cache/`, so repeat
runs and growing archives cost almost nothing. Explorer calls are throttled to ~1/s with
back-off on HTTP 429, per Lichess API etiquette. The local database needs no cache — lookups are
indexed by board EPD, so transpositions merge and queries are instant.

## What comes out

`out/opening_leaks.csv` — one row per flagged decision (position + move you chose), sorted by
`priority` (score points lost, weighted by how often you repeat the mistake):

- **Identity**: `eco`, `opening`, `variation_line` (SAN up to your move), `move_number`, `ply`,
  `player_color`, `your_move`, `fen` (the exact position before your move — paste into any board)
- **Your record**: `your_games`, `your_wins/draws/losses`, `your_score_pct`
- **Database baseline**: `db_move_games`, `db_move_score_pct`, `db_move_popularity_pct`,
  `db_position_games`, `db_position_score_pct`, `score_gap_vs_db_pct`, `lost_points`
- **Engine verdict**: `eval_before_cp` (best available), `eval_after_cp` (what you played),
  `eval_drop_pawns`, `engine_rank_of_your_move`
- **Missed opportunities**: `engine_best_1..3` with `_cp` and `_db_score_pct`, i.e. the engine's
  top choices *and* how humans in your rating pool actually score with them
- `flag`: `WINRATE_DECLINE` (you underperform the database baseline in this exact position),
  `EVAL_DROP` (Stockfish loss ≥ threshold), `OFFBEAT_MOVE` (<2% popularity and below-par results)
- `sample_games`: up to 8 game IDs/URLs to review

`out/variation_summary.csv` — rollup by ECO/opening: decisions, W/D/L, score%.

## How the numbers are defined

- **Eval drop** = `eval(best move)` − `eval(your move)`, both from the mover's point of view at
  the same depth, mates clamped to ±10000 cp. If your move *is* the engine's first choice the
  drop is 0 by construction (no second search needed).
- **Win rate** is a score rate: `(wins + 0.5·draws) / games`, always from your point of view, so
  White and Black rows are directly comparable.
- **Baseline** is the database score for *the same move in the same position*, filtered to your
  rating/speed pool; it falls back to the position-level score if that move is not in the database.
  Positions the database has never seen leave those columns blank rather than reporting zeros.
- A decision is only judged after `--min-games` repetitions, which is what makes a decline
  "consistent" rather than one bad game.

## Layout

```
chessopening/pgn_loader.py   folder walk, PGN parsing, opening-phase ply records
chessopening/explorer.py     Lichess Opening Explorer client (cache, throttle, offline mode)
chessopening/localdb.py      offline SQLite opening database, same lookup() API as the Explorer
chessopening/engine.py       Stockfish UCI wrapper: MultiPV, eval drops, alternatives
chessopening/analyze.py      aggregation, flagging, CSV writers
chessopening/cli.py          argparse entry point (python -m chessopening)
chessopening/bin/stockfish   bundled engine (installed by tools/install_stockfish.py)
chessopening/data/           openings.sqlite (move stats) + eco.tsv (opening names)
tools/install_stockfish.py   platform-aware engine installer
tools/build_local_db.py      builds openings.sqlite from Lichess dumps or your own PGNs
tools/make_sample_pgns.py    generates a synthetic 83-game archive for demos
tests/test_pipeline.py       12 tests: PGN, database, engine, end-to-end CSV contract
```

## Tests

```bash
python tools/make_sample_pgns.py
python -m pytest tests -q      # 12 passed
```

Coverage: PGN discovery and player detection, ply-record correctness, score math, Explorer parsing
and offline behaviour, local-database build/lookup/EPD keying, engine drop detection on a known
piece-losing move, a no-network end-to-end run against the bundled database and engine, and the
CSV column contract. One end-to-end test seeds a clearly-labelled synthetic Explorer response into
the cache so the API path is exercised without touching the network.

## Web dashboard

The same package powers a browser dashboard (`../chess-dashboard/`): drop PGNs, watch the run log,
then browse KPIs, charts, a sortable leak table, and a board view of each flagged position with
Stockfish's alternatives. See `chess-dashboard/README.md` for the API surface and how to run it.

```bash
cd ../chess-dashboard
pip install fastapi uvicorn python-multipart
python api_server.py                 # API on :8000
python -m http.server 8080 -d public # UI on :8080
```
