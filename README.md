# Chess Opening Leak Analyzer

Find the exact points in your openings where you keep losing rating, using your own PGN
archive, a bundled Stockfish build, and a bundled SQLite opening book. Everything runs
offline: no API keys, no rate limits, no network calls.

Two ways to use it:

| | |
| --- | --- |
| `chess_opening_analyzer/` | Python package + CLI. Parses PGNs with python-chess, compares every repeated opening decision against the opening database, runs Stockfish over the first N moves, writes a CSV report. |
| `chess-dashboard/` | Opening Leak Lab — a FastAPI backend and a static front end that wraps the same package: drop PGNs, watch the run log, then browse KPIs, charts, a sortable leak table, and a board view of each flagged position with the engine's alternatives. |

## Setup

The opening database (19 MB) is tracked with [Git LFS](https://git-lfs.com/), so install LFS
before cloning or you will get a small pointer file instead of the real database. The Stockfish
binary is **not** in the repo — it is downloaded per machine so the CPU build matches the host.

```bash
git lfs install
git clone https://github.com/AdLgames/chess-opening-leak-analyzer.git
cd chess-opening-leak-analyzer
make setup                 # or: python chess_opening_analyzer/tools/setup_env.py --dashboard
```

`make setup` installs the Python dependencies, downloads the right Stockfish build, checks the
opening database, and finishes with a short smoke run. It is safe to re-run — every step is
skipped when already satisfied.

Doing it by hand, or without make:

```bash
pip install -r chess_opening_analyzer/requirements.txt
python chess_opening_analyzer/tools/install_stockfish.py          # engine into chessopening/bin/
python chess_opening_analyzer/tools/install_stockfish.py --check   # report what is installed
```

The installer tries the AVX2 build first, falls back to SSE4.1 if the CPU cannot run it, verifies
the binary answers UCI before keeping it, and does nothing when a working engine is already there
(`--force` reinstalls). If the download is blocked, a system engine works too: `apt install
stockfish`, `brew install stockfish`, then pass `--engine /path/to/stockfish` or set
`STOCKFISH_PATH`. Everything except eval-drop detection also runs with `--no-engine`.

Already cloned without LFS? `git lfs install && git lfs pull`. Prefer not to download the book
at all? Clone with `GIT_LFS_SKIP_SMUDGE=1` and build your own with
`python tools/build_local_db.py`.

### Make targets

| Target | Does |
| --- | --- |
| `make setup` | dependencies, engine, database check, smoke run |
| `make engine` / `make engine-check` | install or report the Stockfish build |
| `make test` | the 12-test suite |
| `make demo` | CLI run over the bundled sample archive |
| `make dashboard` | start the dashboard API on :8000 |
| `make clean` | drop `out/`, caches, `__pycache__` |

## Quick start (CLI)

```bash
pip install -r chess_opening_analyzer/requirements.txt
cd chess_opening_analyzer
python -m chessopening --pgn-dir sample_pgns --db local --min-db-games 20 --depth 16 --out-dir out
```

`out/opening_leaks.csv` holds one row per flagged decision, sorted by priority, with the
FEN, your record, the book record, the eval swing, and Stockfish's top three alternatives.

## Quick start (dashboard)

```bash
pip install -r chess_opening_analyzer/requirements.txt fastapi uvicorn python-multipart
cd chess-dashboard
python api_server.py                  # API on :8000
python -m http.server 8080 -d public  # UI on :8080
```

Then open `http://localhost:8080`.

## How a leak is flagged

Score is win% + half of draw%, matching Lichess convention.

- `eval` — Stockfish's evaluation drops by at least the threshold (default 0.8 pawns) on the move you played.
- `win-rate` — a decision you repeat often scores below the book by more than the gap threshold (default 6%).
- `offbeat` — your move is played by under 5% of games in the database for that position.

## What ships in the repo

- `chess_opening_analyzer/chessopening/data/openings.sqlite` — via Git LFS. 157,625 games, 49,327 positions,
  79,999 move rows, 3,810 named openings, built from [Lichess database](https://database.lichess.org/)
  dumps filtered to blitz/rapid/classical, Elo 1500-2100, first 15 moves. Rebuild or extend it with
  `python tools/build_local_db.py`.
- `chess_opening_analyzer/chessopening/data/eco.tsv` — ECO codes and opening names.
- `chess_opening_analyzer/tests/test_pipeline.py` — 12 tests covering PGN parsing, score math,
  database keying, engine drop detection, an offline end-to-end run, and the CSV column contract.
- `chess_opening_analyzer/sample_pgns/` — synthetic 83-game demo archive (player `SamplePlayer`).

An online mode against the [Lichess Opening Explorer](https://explorer.lichess.ovh/) is still
available with `--db lichess`; the local database is the default so the tool works with no network.

The engine directory `chessopening/bin/` is git-ignored: `tools/install_stockfish.py` fills it in
on each machine, and [CI](.github/workflows/tests.yml) exercises that same path on every push.

## Tests

```bash
make test        # or: cd chess_opening_analyzer && python -m pytest tests -q
```
