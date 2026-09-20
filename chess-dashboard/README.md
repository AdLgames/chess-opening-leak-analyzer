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

The page has three states and shows one at a time. Before a run it is a single
decision: a username, "Analyse my games", and a sample archive one click away.
While a run is in flight that collapses to one line and a progress bar. After it,
the report appears — and a cached report boots straight back into it.

Three destinations, each named the same in the nav and in its heading. Macro and
micro no longer share a page:

1. **Dashboard** — what is wrong. The summary band (coverage, leaks, points shed,
   games read, worst opening), one call to action naming how many leaks are still
   open, the chart, and the leak list itself: cost with an inline bar, opening
   over its line, your move with its flags, you vs book, games. Tapping a row is
   how you enter the Clinic.

   The chart has two readings behind one toggle, both drawn as SVG in the page —
   no chart library, so the panel cannot vanish with a CDN. *Points shed* is a
   ranked bar per opening: one series, so one colour, with the value at every tip
   and no gridlines to carry. *You vs book* is a dumbbell — your score and the
   book's from the same positions, the connector between them being the gap —
   with the book in a recessive slate so the subject reads and the reference
   recedes. Both mark colours are steps of the brand hues chosen with
   `scripts/validate_palette.js`: they clear colour-vision separation and 3:1
   against each surface, and the muted brass is relieved by the value labels and
   the table underneath. Hovering any row gives the numbers the chart does not
   print.
2. **Clinic** — how to fix it, one leak at a time. The board is the hero, with
   your record against the book, the eval swing, the engine's alternatives and
   the book moves beside it, and Commit / Not interested / Drill this as the
   actions. A Study/Drill switch turns the same position into a flashcard, and
   the arrows walk the queue in cost order.
3. **Repertoire** — why, and what you have built. The committed tree per colour,
   the holes left in it, coverage, progress between runs, a profile of every
   opening you play with the traps that have caught you, and the book explorer.

On a phone those three are a fixed bar at the bottom rather than a drawer; the
rail returns above 860px.

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

## Theme

One set of tokens at the top of `public/styles.css`, from the brand palette:

| Token | Hex | Where it goes |
| --- | --- | --- |
| `--navy` | `#1B2430` | Ink for all type, the nav rail, primary buttons |
| `--on-navy` | `#F8FAFC` | Type on navy — and, as `--page`, the page itself |
| `--accent` | `#B8935A` | Aged Brass: cost bars, cost numbers, coverage, flag chips. Nothing else |
| `--accent-text` | `#825F2F` | The readable weight of brass, for anything brass has to say in type |
| `--board-light` / `--board-dark` | `#EAE3D2` / `#634E3F` | Ivory Bone and Dark Walnut squares |
| `--highlight` | `#A8A354` | Muted Gold: the last move, and the engine's pick |
| `--slate` | `#3E5265` | Slate Blue: legal moves, selection, hover, secondary borders |
| `--danger` | `#C95246` | Muted Crimson: a king in check, a move that loses ground |

A dark theme is the same tokens from the other side — Deep Navy grounds the page,
Off-White becomes the ink — and follows the operating system unless the footer
switch says otherwise, which is remembered. Severity has three weights rather
than three new hues (`--sev-high` crimson, `--sev-mid` brass, `--sev-low` a
neutral), and the flag chip beside a number always says the same thing in words,
so colour is never the only cue.

The palette is specified for a dark deployment; run light, Deep Navy and Off-White
swap roles — navy becomes the ink and keeps the nav rail, off-white becomes the page.
Every colour that carries type has a `-text` sibling dark enough to clear 4.5:1 on the
page, and the board's coordinates take the colour of the opposite square.

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
