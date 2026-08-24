# Opening Leak Lab — phase 2 requirements

Draft for review. Phase 1 shipped: PGN ingestion, local opening book (157,625 games), bundled
Stockfish 17.1, three leak flags, a dashboard with charts, board view and CSV export, plus a
hosted serverless build. Phase 2 is about turning a one-shot report into something a player
returns to.

## 1. Who uses it

| Persona | What they arrive with | What they want to leave with |
| --- | --- | --- |
| Club player (1200-1900) | A Lichess or Chess.com username, no PGN files, no engine knowledge | "Fix these three lines before your next tournament" |
| Improver with a coach | Exports from several sites, a specific repertoire | Evidence of which lines are actually costing points, in a form the coach can read |
| Tournament preparer | An opponent's games | The opponent's leaks, not their own |
| Returning user | A previous report | Did last month's fix work? |

Phase 1 only really serves the middle row, and only for someone comfortable exporting PGNs.

## 2. Jobs to be done, ranked

1. **Get my games in without exporting files.** Type a username, pick a site and a date range.
2. **Tell me what to do next**, not just what went wrong: a prioritised fix list with the correct
   move, the engine's line, and a reason in words.
3. **Let me practise the fix** in the browser against the engine or the book.
4. **Remember my runs** so improvement is visible over time.
5. **Let me look up any position**, not just the flagged ones.
6. **Give me something shareable** — a report a coach or a training partner can open.

## 3. Requirement tracks

### Track A — Game ingestion (P0)

- A1. Fetch games by username from the Lichess public API (`/api/games/user/{name}`, NDJSON,
  no key required) with filters: time control, rated only, colour, date range, max games.
- A2. Same for Chess.com's public archives endpoint (`/pub/player/{name}/games/archives`).
- A3. Progress feedback while fetching, and a cache so a re-run does not refetch.
- A4. Keep manual PGN upload as the offline path; the analyzer must still run with no network.
- Acceptance: entering a username with 200 blitz games produces a report with no file handling,
  and the same run works offline from a saved archive.

### Track B — Actionable output (P0)

- B1. A "fix list" view: the top 5-10 leaks as cards, ordered by points recoverable, each with
  the position, your move, the book's and engine's preferred move, and a plain-language reason.
- B2. Explain *why* in words, derived from the data ("you play this 9 times and score 11% where
  the book scores 33%; the engine puts your move 3.4 pawns behind c3").
- B3. Group leaks by variation, so one repeated mistake is one item, not five rows.
- B4. Severity model that combines frequency, score gap and engine loss into one number, with the
  weighting visible and adjustable.
- Acceptance: a first-time user can name their three worst lines within 30 seconds of the run
  finishing, without reading the table.

### Track C — Repertoire memory (P1)

- C1. Persist runs (SQLite locally, and a per-browser store in the hosted build).
- C2. Run history with a diff: which leaks disappeared, which are new, which got worse.
- C3. A tracked repertoire — mark a line as "learned" and get told when it leaks again.
- C4. Export/import of the whole history as one file.
- Acceptance: two runs a month apart show a per-leak delta and a headline "points recovered".

### Track D — Interactive board and practice (P1)

- D1. A move tree explorer from the starting position: your frequencies and score next to the
  book's, walk any line, not only flagged ones.
- D2. Play the engine's suggested continuation out on the board, move by move.
- D3. Drill mode: the app plays the opponent's book moves, you have to find the improvement; wrong
  answers repeat later in the session.
- Acceptance: from any flagged position, three clicks to a drill that rehearses the fix.

### Track E — Opponent scouting (P2)

- E1. Run the same analysis on someone else's username and invert the framing ("what to play
  against them").
- E2. Side-by-side: your repertoire against theirs, highlighting where your lines meet.

### Track F — Sharing and reporting (P2)

- F1. A print-ready PDF or a shareable static HTML report with the board diagrams.
- F2. Deep links to a specific position in the dashboard.
- F3. Lichess study export (PGN with comments and variations) so fixes land where people train.

### Track G — Data quality (P1)

- G1. Widen the book beyond the 2013 dumps and 1500-2100 band; let the Elo band and time control
  be chosen at query time so the comparison matches the user's level.
- G2. Show sample-size confidence on every comparison, and suppress claims below a threshold.
- G3. A rebuild script with a documented download-and-ingest path and a size budget.
- Acceptance: a 1300-rated user is compared against 1000-1500 games, not 1500-2100, and every
  percentage carries a game count.

### Track H — Platform (P1)

- H1. Job queue and progress for the hosted build so runs are not bound by the function timeout,
  or a clear "run locally for depth 20+" hand-off.
- H2. Rate limiting and upload validation on the hosted API.
- H3. Accessibility pass (keyboard board navigation, focus order, contrast) and a mobile layout
  pass on the report views.
- H4. Error surfaces: unreadable PGN, username not found, engine missing, book missing.

## 4. Non-functional targets

| Concern | Target |
| --- | --- |
| Local run, 500 games, depth 16 | under 3 minutes on 2 cores |
| Hosted run | inside the function budget, or queued with progress |
| First paint of the dashboard | under 1.5 s, no layout shift on chart load |
| Offline | full local run with no outbound request, always |
| Privacy | uploaded PGNs and fetched games stay on the machine that ran them; nothing sent to a third party |
| Tests | every new analysis rule gets a unit test with a fixed FEN fixture |

## 5. Decisions taken

| Question | Decision |
| --- | --- |
| Scope | Track A (username ingestion) and Track D (board explorer and drills), plus accounts |
| Persistence | Accounts with a hosted database — real sign-in, server-side run history |
| Audience | Both, with username entry as the default path and file upload kept for offline and power use |
| Deferred | Track B fix-list rewrite, Track E scouting, Track F reporting, Track G book widening |

Two consequences worth stating plainly. Accounts mean the hosted build stops being stateless, so
it needs a database, password handling and session management — that is the largest single piece
of phase 2. And the hosted build is not currently deployed: the Vercel token available to me
cannot create deployments, so accounts can be built and tested locally but somebody with deploy
rights has to push them live.

## 6. Track A — username ingestion, detail

### Providers

| Provider | Status | Notes |
| --- | --- | --- |
| Chess.com | Verified working, no key | `GET /pub/player/{user}/games/archives` lists monthly archives; each month returns full PGNs. Requires a descriptive `User-Agent`. |
| Lichess | Needs a fallback | `GET /api/games/user/{user}` returns 404 from this environment while `/api/user/{user}` and single-game export both work. Ship it with an optional personal API token field and a clear message plus a download link when the anonymous call fails. |
| Manual | Keep | File upload and drag-drop stay, and remain the only path that needs no network. |

### Behaviour

- A1. One input: username, provider (auto-detect where possible), colour, time controls, rated
  only, date range, max games.
- A2. Fetch with a monthly cursor for Chess.com, a `since`/`until` window for Lichess, one request
  at a time, honouring 429 with a backoff.
- A3. Cache raw archives on disk keyed by provider, user and month, so re-running is instant and
  offline. Cache is what makes drills usable without refetching.
- A4. Normalise both providers into the same game records the parser already consumes, keeping
  result, colour, time control, rating and date.
- A5. Progress: archives discovered, games fetched, games parsed, with a cancel.

## 7. Track D — explorer and drills, detail

- D1. Move tree from the initial position: at each node show your games, your score, the book
  score, the engine's preferred move if evaluated, and the delta. Click to walk, breadcrumb to
  jump back, keyboard arrows to step.
- D2. Any node can be sent to the engine on demand rather than only at run time.
- D3. Drill mode: start at a flagged position with your side to move; the app answers with the
  book's most common reply. Correct answer advances the line, a wrong answer shows the engine
  line and requeues the position later in the session.
- D4. Session summary: positions attempted, first-attempt accuracy, positions still failing, and
  which of those map to open leaks.
- D5. Board rendering with real piece assets, legal-move validation in the browser, and no engine
  round-trip for move legality.

## 8. Accounts and data model

- Email plus password, hashed with a modern KDF, and an HttpOnly session cookie. No third-party
  identity provider in phase 2.
- Tables: `users`, `sessions`, `runs` (options, summary, provider, username), `leaks` (per-run
  rows), `drill_attempts`, `repertoire_marks`, and `archive_cache` metadata.
- Local mode keeps working with no account at all: the same schema in SQLite, a single implicit
  user, no login screen. Accounts exist for the hosted build.
- A run belongs to a user; nothing is readable across users. Deleting an account deletes its runs.
- Postgres for the hosted side, SQLite locally, one data-access layer over both.

## 9. Build order

1. Ingestion library with the provider adapters, cache and tests, wired into the CLI first. **Done.**
2. Username panel in the dashboard, replacing the upload card as the default, upload behind a tab. **Done.**
3. Data layer plus accounts, local-first with the implicit user, then login on the hosted build.
4. Move tree explorer over the existing database and run output. **Done.**
5. Drill mode on top of the explorer, then the session summary. **Done.**
6. Run history and per-leak deltas, which fall out of the data layer almost for free.

## 10. Track A as built

- `chessopening/ingest.py`: `FetchOptions`, `fetch_games`, `lookup_player`, standard library only.
  Chess.com walks monthly archives newest first and stops at the game cap; Lichess uses one
  windowed export request. Both honour 429 with a backoff and cache to
  `~/.cache/leaklab/archives`, so repeat runs make no requests.
- CLI: `--user`, `--provider`, `--max-games`, `--time-classes`, `--include-unrated`,
  `--since`, `--until`, `--lichess-token`, `--archive-cache`, `--refresh`. `--pgn-dir` still
  works and is now optional.
- API: `POST /api/analyze` accepts `source=username` with the same filters, streams fetch
  progress into the run log, and returns ingest failures with a hint and a manual-download
  link. `GET /api/lookup` confirms a username and returns a small profile card.
- Dashboard: three source tabs with the account tab first. Site toggle, username field with
  a debounced profile check, ratings card, games-to-read slider, date window, time-control
  chips, rated-only and refetch switches, and a Lichess token field that appears only for
  Lichess. The last account used is remembered locally.
- Hosted build mirrors all of it, capped at 120 fetched games per invocation.
- Tests: 15 ingest tests with a stubbed HTTP layer, covering month walking, the cap,
  filters, the date window, cache reuse, bad usernames and both providers' failure paths.
  Suite total 27 passing.

## 11. Track D as built

- `chessopening/board.py`: `board_from(fen, moves, san)` rebuilds a position from a FEN, a UCI
  list, or a replayed SAN line — the SAN path is what gives a report row a real move history, so
  the opening name and move numbers are correct rather than inferred from a bare FEN.
  `legal_moves` returns uci, san, from, to, promotion, capture, check, mate and the FEN after.
  `book_stats` returns totals, win/draw/loss and per-move shares from the local book, `name_for`
  walks the history back to the last named opening, and `engine_lines` holds one long-lived
  Stockfish process behind a lock with a JSON cache on disk.
- API, both locally and hosted: `GET /api/position` (legality, naming, book), `POST /api/engine`
  (multi-PV lines on demand), `GET /api/openings` (named-opening search). The hosted build caps
  board evaluations at depth 12 and 3 lines and caches them under `/tmp`.
- `public/board.js`: dependency-free board component — Unicode pieces, click-to-select with legal
  targets, capture rings, promotion picker, last-move highlight, SVG arrows in three colours
  (played, engine, book), flip, plus cached position and engine calls and the book/engine renderers.
- `public/study.js`: the three panes. Review (D1, D2, D5) opens on the flagged position with your
  move and the alternatives, and the book answers moves you play. Practice (D3, D4) drills the 15
  costliest leaks, grades each attempt against Stockfish by centipawn loss, and keeps a session
  score. Library walks any named opening with book statistics and engine lines at each node.
- Still open from the track: keyboard stepping, requeueing failed drills later in the session, and
  persisting drill history — that last one waits on the accounts work in section 8.
