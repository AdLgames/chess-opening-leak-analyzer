# Opening Leak Lab — dashboard

Web front end for the chess opening leak analyzer. Everything runs locally: the
bundled Stockfish binary and the bundled SQLite opening book. No API keys, no
network calls, no rate limits.

```
chess-dashboard/
  api_server.py        FastAPI backend (port 8000)
  public/              static front end (index.html, styles.css, app.js)
  chessopening/        analyzer package + bin/stockfish + data/openings.sqlite
  sample_pgns/         demo archive (83 games, player "SamplePlayer")
  tools/               install_stockfish.py, build_local_db.py, make_sample_pgns.py
```

## Run it

```bash
pip install -r ../chess_opening_analyzer/requirements.txt fastapi uvicorn python-multipart
python api_server.py                 # serves the API on :8000
python -m http.server 8080 -d public # or any static server
```

Open `http://localhost:8080`. The front end auto-detects the API at
`http://localhost:8000` when served locally.

## What the page does

1. **Feed it your games** — drop `.pgn` files (Lichess, Chess.com, SCID, ChessBase
   exports) or run the demo archive. Options: player name (blank = auto-detect the
   most frequent name), colour, engine depth, opening length, minimum games per
   line, eval-drop threshold, score-gap threshold, minimum book games, and a
   "skip engine" switch for statistics-only runs.
2. **Overview** — games parsed, repeated decisions, leaks flagged, points shed,
   engine drops, worst opening.
3. **Where the points go** — half-points lost by opening, and your score versus the
   book score for the same move.
4. **Leak table** — every flagged decision, sortable, filterable by flag
   (`eval` / `win-rate` / `offbeat`) and colour, with free-text search.
5. **Position detail** — the board drawn from the FEN, your record versus the book,
   the eval swing, and Stockfish's top three alternatives with their book scores.
   Copy the FEN or open the position on Lichess.
6. **Engine & data** — provenance for the engine build and the opening database.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/meta` | engine id, database stats, sample archive info, defaults |
| POST | `/api/analyze` | multipart `files[]` (or `use_sample=true`) plus run options → job id |
| GET | `/api/jobs/{id}` | status, elapsed time, streaming log |
| GET | `/api/report/{id}` | summary KPIs, per-opening rollup, flagged rows |
| GET | `/api/report/{id}/csv` | the same report as CSV |
| GET | `/api/sample-archive` | demo PGN download |
| GET | `/api/health` | liveness |

Uploads are capped at 40 MB per run and rejected unless they end in `.pgn`. Jobs
and their eval cache live under `/tmp/leaklab-jobs/`.

## Notes

- The score used everywhere is win% + half of draw%, matching Lichess convention.
- `eval` flags a Stockfish swing of at least the eval-drop threshold; `win-rate`
  flags a repeated decision that scores below book by more than the gap
  threshold; `offbeat` flags a move played by under 5% of book games.
- The dashboard shares the analyzer package, so a CLI run and a dashboard run on
  the same PGNs produce the same CSV.
