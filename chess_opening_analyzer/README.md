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
python tools/build_local_db.py --months 2026-08 --speeds blitz,rapid,classical \
    --max-moves 20 --max-games 500000 --min-move-games 20
python tools/check_book.py --expect-moves 20 --max-mb 35    # before committing it
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

Two settings the analyser cares about, and will tell you about at runtime if they are missing:

* `--max-moves` decides how deep theory goes. The analyser follows the book past its own
  fixed cutoff for as long as the book still covers the position, so a book built to move
  15 caps that at move 15 no matter what the run asks for.
* Rating bands are written automatically: every game is counted into its own band and into
  `all`, so a 1400 can be compared against 1200-1600 rather than against everybody at once.
  A book built before bands existed has only `all` rows, and every run says so.

  This is why the build above sets **no** `--min-elo/--max-elo`. Filtering the corpus by
  rating and then asking it for bands gives bands that mostly do not exist: the shipped
  book's 1500-2100 filter leaves `u1200` and `2400+` empty, `all` meaning "1500-2100
  players" rather than everybody, and a 1400 falling back through the neighbours to that
  same narrow slice. The bands are the stratification now, so the corpus should span them.
  `--max-games` caps the work instead — it stops the stream, so a recent month costs a
  fraction of its full size.

`check_book.py` reports what a book actually contains and fails on both of those, plus the
empty, truncated and still-an-LFS-pointer cases. Worth running before committing one: the
build takes hours, and "deploy it and see" is a slow way to find out it was shallow.

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
| `--thin-games 6` | Below this many repetitions a finding is flagged `thin` rather than dropped |
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
runs and growing archives cost almost nothing. Evaluations are keyed on the EPD — the FEN
without the move counters — plus the engine build and depth, so one entry serves a position
however it was reached and whichever game it came from. Explorer calls are throttled to ~1/s with
back-off on HTTP 429, per Lichess API etiquette. The local database needs no cache — lookups are
indexed by board EPD, so transpositions merge and queries are instant.

## What comes out

`out/opening_leaks.csv` — one row per flagged decision (position + move you chose), sorted by
`cost`: frequency x severity, shrunk by `games / (games + 4)` so a habit seen three times cannot
outrank one seen thirty.

- **Identity**: `eco`, `opening`, `variation_line` (SAN up to your move), `move_number`, `ply`,
  `player_color`, `your_move`, `fen` (the exact position before your move — paste into any board)
- **Your record**: `your_games`, `your_wins/draws/losses`, `your_score_pct`
- **Database baseline**: `db_move_games`, `db_move_score_pct`, `db_move_popularity_pct`,
  `db_position_games`, `db_position_score_pct`, `score_gap_vs_db_pct`, `lost_points`
- **Engine verdict**: `eval_before_cp` (best available), `eval_after_cp` (what you played),
  `eval_drop_pawns`, `engine_rank_of_your_move`
- **Missed opportunities**: `engine_best_1..3` with `_cp` and `_db_score_pct`, i.e. the engine's
  top choices *and* how humans in your rating pool actually score with them
- `flag`, one or more of: `underperforming` (you score below the database baseline in this exact
  position), `blunder` (Stockfish loss ≥ threshold), `unfamiliar` (<2% popularity and below-par
  results), `thin` (fewer than `--thin-games` repetitions, so the sample is too small to act on)
- `sample_games`: up to 8 game IDs/URLs to review

`out/variation_summary.csv` — rollup by ECO/opening: decisions, W/D/L, score%.

`out/opening_profiles.json` — one profile per opening family per colour, plus the traps
this player walked into:

- **Per opening**: `games`, W/D/L, `score_pct` against `book_score_pct` (what the book gets
  from the same positions) and the `gap_pct` between them, `first_break` (the move number
  the line stops holding), `breaks` (the spread of break points), `cost`, and the flagged
  decisions with `play_instead` — the engine's move when the run had one, otherwise the
  book's best move with at least 20 games.
- **`break_moves`**: the run-wide spread of where openings break down, by move number.
- **`worst_against`**: the openings whose score falls furthest below the book, weighted by
  how often they come up. Openings with fewer than three games are never called a weakness.
- **`traps`**: which of the catalogued trap lines the player met, and how often they walked
  in rather than holding.

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
- **Cost** = `(score points shed per game + eval drop / 4) x games x games / (games + 4)`. The
  last term is the cautious part: it holds a finding back while its sample is small, and
  approaches 1 once you have played the position often. Every row carries the
  `cost_version` that produced it, so the formula can change without silently reshuffling
  old reports, and `COST_EXPLAINER` — served by `/api/meta` — is the one description of it.

## Layout

```
chessopening/pgn_loader.py   folder walk, PGN parsing, opening-phase ply records
chessopening/explorer.py     Lichess Opening Explorer client (cache, throttle, offline mode)
chessopening/localdb.py      offline SQLite opening database, same lookup() API as the Explorer
chessopening/engine.py       Stockfish UCI wrapper: MultiPV, eval drops, alternatives
chessopening/analyze.py      aggregation, flagging, cost, CSV writers
chessopening/profiles.py     per-opening profiles: record vs book, break point, what to play instead
chessopening/traps.py        matches games against the known-trap catalogue
chessopening/demo.py         the cached demo report both backends serve
chessopening/cli.py          argparse entry point (python -m chessopening)
chessopening/bin/stockfish   engine, fetched per machine by tools/install_stockfish.py (git-ignored)
chessopening/data/           openings.sqlite (move stats), eco.tsv (opening names), traps.json (trap catalogue)
tools/install_stockfish.py   platform-aware engine installer (--check, --force, CPU-build fallback)
tools/setup_env.py           one-command bootstrap: deps, engine, database check, smoke run
tools/build_local_db.py      builds openings.sqlite from Lichess dumps or your own PGNs
tools/make_sample_pgns.py    generates a synthetic 83-game archive for demos
tools/bake_demo_report.py    pre-computes the dashboard's demo report so it loads instantly
tests/test_pipeline.py       PGN, database, engine, end-to-end CSV contract
tests/test_summary.py        the roll-up the dashboards read: totals, flags, coverage denominator
tests/test_profiles.py       per-opening profiles: families, break points, recommendations
tests/test_traps.py          the trap catalogue's consistency and the scan over a player's games
```

## Tests

```bash
python tools/make_sample_pgns.py
python -m pytest tests -q
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
