# Chess Opening Leak Analyzer

Find the exact points in your openings where you keep losing rating, using your own PGN
archive, a bundled Stockfish build, and a bundled SQLite opening book. Everything runs
offline: no API keys, no rate limits, no network calls.

Two ways to use it:

| | |
| --- | --- |
| `chess_opening_analyzer/` | Python package + CLI. Parses PGNs with python-chess, compares every repeated opening decision against the opening database, runs Stockfish over the first N moves, writes a CSV report. |
| `chess-dashboard/` | Opening Leak Lab — a FastAPI backend and a static front end that wraps the same package: drop PGNs, watch the run log, then browse KPIs, charts, a sortable leak table, and a board view of each flagged position with the engine's alternatives. |

## Cloning

The Stockfish binary and the opening database are tracked with [Git LFS](https://git-lfs.com/),
so install it once before cloning or you will get small pointer files instead of the real assets.

```bash
git lfs install
git clone https://github.com/AdLgames/chess-opening-leak-analyzer.git
```

Already cloned without LFS? Run `git lfs install && git lfs pull`. If you would rather skip the
98 MB download entirely, clone with `GIT_LFS_SKIP_SMUDGE=1` and then regenerate both files with
`python tools/install_stockfish.py` and `python tools/build_local_db.py`.

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

- `chess_opening_analyzer/chessopening/bin/stockfish` — Stockfish 17.1 (Linux, AVX2), via Git LFS. Run
  `python tools/install_stockfish.py` to fetch the right build for another platform.
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

## Tests

```bash
cd chess_opening_analyzer && python -m pytest tests -q
```
