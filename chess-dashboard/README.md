# Opening Leak Lab — dashboard

Web front end for the chess opening leak analyzer. The analysis runs locally: the
bundled Stockfish binary and the bundled SQLite opening book, no API keys and no
rate limits. The one outbound request is the game archive you ask it to fetch,
straight to Chess.com or Lichess; uploaded PGNs make even that unnecessary.

```
chess-dashboard/
  api_server.py        FastAPI backend (port 8000)
  public/              static front end (index.html, styles.css, app.js,
                       vocab.js = the product's vocabulary, store.js = what the
                       browser remembers, repertoire.js = repertoire + progress)
  chessopening/        analyzer package (or reuse ../chess_opening_analyzer/chessopening)
  sample_pgns/         demo archive (83 games, player "SamplePlayer")
  tools/               install_stockfish.py, build_local_db.py, make_sample_pgns.py
```

## Run it

```bash
python ../chess_opening_analyzer/tools/setup_env.py --dashboard   # deps + engine + checks
python api_server.py                 # serves the API on :8000
python -m http.server 8080 -d public # or any static server
```

Open `http://localhost:8080`. The front end auto-detects the API at
`http://localhost:8000` when served locally.

## What the page does

The page has three states and shows one at a time. Before a run it is a single
decision: a username, "Analyse my games", and a sample archive one click away.
While a run is in flight that collapses to one line and a progress bar. After it,
the report appears — and a cached report boots straight back into it.

Five destinations, each named the same in the nav and in its heading:

1. **Report** — a summary band (coverage, leaks, points shed, games read, worst
   opening), one chart panel with a toggle between points shed and you-vs-book, and
   the leak table: cost with an inline bar, opening over its line, your move with
   its flags, you vs book, games. Rows are capped with "Show all" and become cards
   on a narrow screen. Selecting one fills the fix panel below: the board, your
   record against the book, the eval swing, Stockfish's alternatives with their
   book scores, the book moves from the position, and a live engine pane. From
   there a finding can be committed, dismissed or sent to practice.
2. **Repertoire** — the lines you have committed as a move tree per colour, the
   holes left in it ranked by how often they come up, and the coverage figure.
3. **Practice** — the drill set built from the report, scored as you go.
4. **Progress** — coverage per run, the leaks that have gone and what they were
   costing you, and per-position drill retention with a review date.
5. **Library** — the opening explorer.

Run options beyond colour and how many games to read live behind "Advanced
settings", which stays shut until you open it and then remembers that. Engine and
book provenance, the cost formula and the flag legend are a footer dialog.

Exports: the repertoire as PGN (variations nested), the drill set as PGN with
FENs, the leak table as CSV, and the repertoire as a Lichess import.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/meta` | engine id, database stats, sample archive info, defaults |
| POST | `/api/analyze` | multipart `files[]` (or `use_sample=true`) plus run options → job id |
| GET | `/api/jobs/{id}` | status, elapsed time, streaming log |
| GET | `/api/report/{id}` | summary KPIs, per-opening rollup, flagged rows |
| GET | `/api/report/{id}/csv` | the same report as CSV |
| GET | `/api/demo-report` | a finished sample run, cached so the demo is instant |
| GET | `/api/sample-archive` | demo PGN download |
| GET | `/api/health` | liveness |

Uploads are capped at 40 MB per run and rejected unless they end in `.pgn`. Jobs
and their eval cache live under `/tmp/leaklab-jobs/`.

## Notes

- The score used everywhere is win% + half of draw%, matching Lichess convention.
- Findings are ranked by **cost**: frequency x severity, held back while the sample
  is thin. The flags are `blunder` (an eval swing of at least the eval-drop
  threshold), `underperforming` (scores below book by more than the gap threshold),
  `unfamiliar` (a move almost nobody plays, and not working for you) and `thin`
  (too few games to act on yet). `public/vocab.js` is the only place they are
  given user-facing names.
- Your repertoire decisions, drill history and last report are kept in the
  browser's local storage, never on the server.
- The demo report is cached. `python ../chess_opening_analyzer/tools/bake_demo_report.py`
  writes `demo_report.json` here, and the server serves that instead of running
  the pipeline.
- The dashboard shares the analyzer package, so a CLI run and a dashboard run on
  the same PGNs produce the same CSV.

## If the engine is missing

The dashboard degrades instead of failing: the footer status dot turns amber, a notice on the
input screen shows
the install command, and "Faster, no engine" is switched on so statistics-only runs still work. Install
the engine with `python ../chess_opening_analyzer/tools/install_stockfish.py` and reload.
