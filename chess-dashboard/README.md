# Opening Leak Lab — dashboard

Web front end for the chess opening leak analyzer. The analysis runs locally: the
bundled Stockfish binary and the bundled SQLite opening book, no API keys and no
rate limits. The one outbound request is the game archive you ask it to fetch,
straight to Chess.com or Lichess; uploaded PGNs make even that unnecessary.

```
chess-dashboard/
  api_server.py        FastAPI backend (port 8000)
  public/              index.html + landing.css/.js = the front page
                       og.png, robots.txt, sitemap.xml
  public/app/          the tool itself (index.html, styles.css, app.js,
                       vocab.js = the product's vocabulary, store.js = what the
                       browser remembers, repertoire.js = repertoire + progress,
                       explorer.js = the personal openings explorer)
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

Open `http://localhost:8080` for the front page, or go straight to
`http://localhost:8080/app/` for the tool. The front end auto-detects the API at
`http://localhost:8000` when served locally.

## The two pages

`/` is the front page: what the product is, how it works, a sample report and one
field. Submitting it hands over to `/app/?provider=…&user=…&run=1`, and the tool
starts that run on arrival rather than asking for the username a second time.
`/app/?demo=1` opens the sample archive; `/app/?privacy=1` opens the privacy note.
Each of those is read once and then cleared from the URL, so a reload does not
repeat it.

Both pages run the same type system — Instrument Serif for the display line,
IBM Plex Sans for the interface, IBM Plex Mono wherever characters have to line
up (notation, FENs, evals) — from one Google Fonts request that is byte-identical
on both, so moving between them costs no extra download.

Both pages run the brand palette. The front page uses its dark half — Deep Navy
bands, Off-White type, Aged Brass for branding and the call to action — and the
tool uses its light half; the board, the move that loses ground (Muted Crimson)
and the one to play instead (Muted Gold) are the same colours on both.

## What the tool does

The app opens on **Today**. No games or account are needed to explore openings
or save choices on the current device. The four destinations are always available:

1. **Today** — a starting point for new visitors, or a way back to the latest
   saved line. Existing personal game findings can lead into position review.
2. **Explore** — Italian, Caro-Kann and Queen’s Gambit starting points, a legal-move
   board, named-opening/ECO search, SAN/FEN entry and book results. Save a line with
   a side, name and note; its actual move order is retained. These are opening
   guides and database exploration, not a reviewed lesson programme.
3. **Repertoire** — saved choices grouped by side. Open any card on the Explore
   board. The existing variation tree and personal game findings are available
   under a disclosure, and **Build a line** opens the existing prep editor.
4. **Progress** — preparation, recorded practice and optional game evidence shown
   separately. Existing run comparisons and drill schedules remain available.

Desktop uses a compact sidebar; phones use four labelled bottom-navigation
items. Hash routes support direct links and browser Back/Forward. Old
`#dashboard`, `#clinic` and `#prep` links still work, resolving to contextual
`#progress/games`, `#training` and `#repertoire/edit` routes. Practice returns to
its entry screen. Game analysis is reachable from Tools, Today and Progress.

Existing analysis still supports account fetch, PGN upload, the sample report,
engine tools, filters, study/drill modes and CSV/PGN/Lichess exports. Its empty,
running and report states are contained within the game-analysis screen. The
analysis/account authentication rules are unchanged; they do not gate Explore.

Saved repertoire choices, drill records, runs and preferences retain their
`leaklab:` localStorage keys and existing account API shape. A version-1 baseline
backs up existing working data to `leaklab:backup:v0` without rewriting records.
Explicit sign-out/deletion clears that backup with the working copy. New optional
line metadata also survives account sync. Save feedback confirms device storage
only, and reports a tab-only copy if persistence fails.

See [milestone review and screenshots](../docs/foundation-milestone-review.md).

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

## Theme

`public/app/styles.css` retains shared component styles. `workspace.css` supplies
foundation tokens and responsive layouts: warm off-white surfaces, deep green
actions, cream/green squares, display serif headings and legible interface type.
SVG pieces scale with their squares. Existing explicit light/dark preferences
and system-theme support remain available. Controls have visible focus states;
board moves support keyboard and touch, with a button-based book-move alternative.

## Browser tests

```bash
pip install -r ../chess_opening_analyzer/requirements.txt fastapi uvicorn python-multipart pytest playwright
python -m playwright install --with-deps chromium
python -m pytest tests -q
```

The tests start an isolated local API/static server automatically. To use an
existing Chromium install, set `LEAKLAB_CHROMIUM=/usr/bin/chromium`. CI runs these
journeys alongside the existing Python suite. Browser tests use real chess/book
endpoints; targeted network failures and account availability are simulated.

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
- The explorer's data rides along in the report summary as `explorer`; the analyzer
  builds it in `profiles.py` and `traps.py`. A trap is only reported when a game
  followed its line move for move, so transpositions are never claimed as hits.
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
