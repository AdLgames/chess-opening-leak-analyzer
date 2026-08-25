# Improvement plan

Derived from two audits of `fdc9685`: a **repertoire gap audit** (does the tool help somebody
build an opening repertoire?) and a **consumer readiness review** (can a non-technical person
reach and understand it?). This file is the working plan that merges both into one ordered
sequence, and it is the place to record status as work lands.

Finding IDs used below come from those audits:

| Prefix | Audit | Theme |
| --- | --- | --- |
| `R1`–`R5` | Repertoire gap | The repertoire has no representation in the data model |
| `S1`–`S5` | Repertoire gap | Statistics the learner is asked to trust |
| `X1`–`X6` | Repertoire gap | Experience, access, claims |
| `C01`–`C08` | Consumer readiness | Stages of the journey from arrival to return |

---

## The two problems, stated once

**Problem one — the tool has no concept of a repertoire.** Everything is keyed to
`(position, the move you actually played)`. That makes it impossible to say "against 1.e4 I play
the Caro-Kann", which in turn makes it impossible to distinguish *forgetting your line* from
*your line being bad* — opposite problems with opposite fixes — and impossible to say anything
about lines the player will face but has not yet met.

**Problem two — there is no service.** The hosted build was never deployed, so the documented
route to using this software runs through Git LFS, a 79 MB engine download and two local servers.
Until a URL exists, no amount of product work is reachable by anyone.

These are independent. Phase 0 below is worth doing under either, because shipping a consumer
product on top of statistics that can be wrong just distributes bad advice faster.

---

## Principles

1. **Never state a number more precisely than the evidence supports.** A percentage without a
   sample size is a lie of omission; a percentage from three games is mostly noise.
2. **The sentence is the product, the table is the appendix.** A learner needs to know what to do,
   not what the centipawn delta was.
3. **Every phase ships something usable.** No phase exists only to enable the next one.
4. **Offline and local stay first-class.** The hosted build is an additional surface, never a
   replacement, and the CLI must keep working with no network.
5. **Reuse before building.** The review pane already plays lines out; the book already knows reply
   frequencies. Most of the plan below is assembly, not invention.

---

## Phase 0 — Make the numbers trustworthy  ·  `S1` `S2` `S5`

**Status: done**

The highest-severity correctness problem in the codebase. `min_db_games` gates the *position*
total, but `PositionStats.move()` returns statistics for a move seen as few as twice, so
`db_move_score_pct` can read a confident `100.0` drawn from two games in a 2013 dump — and
`score_gap_vs_db_pct`, `lost_points` and `priority` all inherit that noise straight to the top of
the report. On the player's side, `min_games` of 3 means "you score 33%" is one of only four values
three games can produce, rendered to one decimal beside a figure drawn from thousands.

### Work

- [x] Score confidence intervals for win/draw/loss records, using the trinomial variance of the
      score rather than a binomial approximation (score is `win + 0.5·draw`, not a coin flip).
- [x] Shrink a book move's score toward the position mean in proportion to its sample size, so a
      2-game move contributes almost nothing and a 2000-game move is taken at face value.
- [x] Require a minimum number of book games on the *move* before it may be used as a baseline at
      all; fall back to the position score below that.
- [x] Suppress `WINRATE_DECLINE` unless the player's score is below the baseline even at the
      generous end of its own confidence interval.
- [x] Rank by a conservative points-lost estimate, so thin evidence sorts down on its own instead
      of needing to be filtered out by hand.
- [x] Carry sample sizes and a confidence label through the CSV, the API and the dashboard, and
      never render a personal score to a decimal place.
- [x] Tests with fixed records covering: tiny samples not flagged, large samples still flagged,
      shrinkage behaviour, interval maths.

### Acceptance

A move the player has made three times, scoring 33% against a book move with four games, produces
no flag. The same 33% over twenty games against a well-sampled book move still does. Every
percentage on screen is accompanied by the count behind it.

### Calibration note

The confidence test is one-sided at 80% (`Z_CONFIDENCE`), not the 90% first tried. At 90% a
player scoring 11% over 9 games against a 23% baseline is not flagged — a real and useful
finding thrown away. In a coaching tool a missed leak costs as much as a spurious one, so the
threshold is set where it suppresses three-game noise without suppressing nine-game signal, and
is exposed as `analyze(confidence_z=)` for anyone who disagrees.

---


## Phase 1 — Say it in words  ·  `S5` `C04` `X2` (`B1`/`B2` from Phase 2 requirements)

**Status: done, bar one deferred item**

The vocabulary on screen is `EVAL_DROP`, `WINRATE_DECLINE`, `OFFBEAT_MOVE`, centipawns, MultiPV,
FEN, EPD, and a priority formula printed as `points lost + eval drop × games × 0.25`. The target
reader is a club player who knows none of these terms. The numbers to write a plain sentence are
all already computed.

### Work

- [x] Generate one plain-language explanation per flagged row, server-side, from the figures
      already in hand, and carry it as a first-class CSV column so the CLI, the API and both
      dashboards share one wording.
- [x] Show the sentence as the leading element of the finding panel, above the figures.
- [x] Report personal scores as whole numbers with the record behind them, and mark low-confidence
      rows in the table.
- [ ] Move the remaining figures behind a "details" toggle. *Deferred: with the sentence leading
      the panel and the table now in plain English, the six remaining stats read as support rather
      than noise. Worth revisiting when the mobile layout lands, where the space actually matters.*
- [x] Promote a "fix list" of the top three findings to directly under the run panel, above the
      table (`X2`), each one a group rather than a row.
- [x] Replace flag codes with human labels throughout the UI — "gives ground", "scores badly",
      "rare move" — with the reason on hover, and relabel the jargon column headings. The codes
      stay in the CSV for anyone parsing it. Verified: no raw code appears on the rendered page.
- [x] Show both halves of the ranking on every finding — how often it happens and what it costs
      each time — so the order is readable rather than asserted (`S5`).

### Acceptance

A first-time user can name their three worst lines within 30 seconds of the run finishing, without
reading the table.

---

## Phase 2 — One hole, one fix  ·  `R3`

**Status: done**

Nodes are keyed `(epd, uci)`, so a single bad decision at move 6 surfaces again as its downstream
consequences at moves 8, 10 and 12, each competing separately for the top of the report. The
learner sees five problems where they have one, and fixing the earliest dissolves the rest.

### Work

- [x] Group flagged rows by line prefix in `summary.group_by_line`, shared by the local API and
      the hosted function so both dashboards get it at once.
- [x] Report the earliest divergence in each branch as the headline, with downstream leaks nested
      beneath it. Colours never nest into each other — the player cannot be both sides of one game.
- [x] Sort by points summed across the branch, since fixing the headline makes the rest moot.
- [x] Keep the flat CSV as-is for compatibility; grouping is a view over it.
- [x] Tests covering causation vs a shared opening prefix, out-of-order rows, and branch costs.

### Acceptance

A player who repeats one bad move at move 6 sees one finding, not five, and the nested rows explain
why the rest of the line went wrong. **Met**: on the demo archive six flagged rows collapse to four
findings — `2...d6` folds into `1...e5` (Philidor) and `2...dxc4` into `1...d5` (Queen's Gambit
Accepted), each headline carrying its branch's combined cost.

---

## Phase 3 — The repertoire object  ·  `R1` `R2`

**Status: coverage done; repertoire persistence and re-labelling still open**

The structural gap. A repertoire tree lets the report distinguish memory failures from bad lines,
and — more valuable — lets the tool talk about lines the player has *not* faced, which is the
question a club player actually arrives with.

### Work

- [x] A repertoire tree per side, inferred in `repertoire.build_repertoire`: at every position
      the player reached, the move they choose most often is what they intend, with `share`
      recording how settled that choice is. Nobody builds a tree by hand — their games describe one.
- [x] Coverage pass (`repertoire.find_gaps`): walk the tree from move one, follow the intended move
      at the player's turn, fan out over the book's replies at the opponent's, and multiply
      probabilities down each branch. Report replies that are both *likely* and *unfamiliar*,
      ranked by how often a real opponent reaches them.
- [x] Written to `repertoire_coverage.csv`, carried in the run summary, and shown on the dashboard
      as "What you're not ready for".
- [x] Tests over a hand-built stub book: intent from plurality, compounding probability, rare
      sidelines pruned, thin book positions making no claims, depth limits, wording.
- [ ] Persist the tree so the player can correct it, rather than re-inferring it every run.
- [ ] Re-label every finding as *off-book* (you know this, you played something else), *weak book*
      (your intended move is the problem) or *uncharted*. Needs the persisted tree above.

### Acceptance

The report can say: "3.e5 appears in 41% of your Caro-Kanns from here. You have faced it twice and
have no prepared answer." **Met**: against a 900-game book the demo player — who opens 1.e4 — is
told that 1...c6 appears in 19% of games and they have never once faced it, followed by the French
at 10% and the Philidor at 7%. The run-over-run comparison waits on Phase 6.

---

## Phase 4 — Real training  ·  `R4` `S4`

Practice currently takes the top 15 rows, asks for one move, grades it against a depth-12 engine
search, and forgets everything on reload. Opening memory is built by recalling a sequence,
repeatedly, over days.

### Work

- [ ] Play the line out to the repertoire's target depth with the book answering — reuse of the
      review pane, not new machinery.
- [ ] Requeue failed positions later in the same session.
- [ ] Persist attempts and schedule reviews on an SM-2-style interval. Feature-detect
      `localStorage` rather than disabling persistence everywhere because one preview iframe
      blocks it.
- [ ] Grade against the union of engine moves within tolerance and well-sampled book moves, and
      say so explicitly when the answer is the main line (`S4`).

### Acceptance

From any finding, three clicks to a drill that rehearses the whole line, and a session that
remembers what was missed last time.

---

## Phase 5 — Become a service  ·  `C01` `C02` `C07` `R5`

Everything above is reachable only by someone who can run a terminal. This phase is what turns it
into something a person can visit.

### Work

- [ ] Deploy the hosted build; put a domain on it; invert the README so the link comes first and
      the clone instructions become the "run it yourself" section.
- [ ] Replace the single synchronous 60-second function with a job queue and worker keyed by job
      id, so a closed tab does not lose a run.
- [ ] Return the statistics pass immediately (it needs no engine) and let engine results refine the
      report as they arrive, replacing the animated bar that currently measures nothing.
- [ ] Persist finished reports so a job id is a permanent, re-openable link.
- [ ] Public read-only report URLs plus an Open Graph image of the top three findings, and a share
      button (`C07`).
- [ ] PGN export with variations and comments, importable into a Lichess study (`R5`).
- [ ] Mobile-first report layout: one finding per full-width card, board at the top (`C07`).

### Acceptance

A person can open a link on a phone, type a username, and get a readable report they can send to a
friend.

---

## Phase 6 — A reason to return  ·  `C06`

No accounts, no history, no saved report; the last username used lives in a plain variable.
Improving at chess is a months-long habit.

### Work

- [ ] Device-local run history in IndexedDB — no backend, no signup, immediate run-over-run
      comparison.
- [ ] Per-finding deltas between runs: gone, new, worse.
- [ ] Accounts, once there is a reason: sync across devices, and email when a fix stops leaking.
- [ ] Scheduled re-analysis, so the user does not have to remember to re-run.

---

## Phase 3b — Deep evaluation without the compute  ·  `S4`

**Status: ingest built; needs one real run against the published dataset**

Stockfish is already the strongest open-source engine, so the compute problem was never
which engine to run — it was running it at all, on demand, per user, at a depth the budget
allows. Lichess publishes Stockfish evaluations for hundreds of millions of positions under
CC0, and opening positions are the most analysed positions in existence, so most of this
work has already been done by somebody else at depths worth far more than depth 12.

### Work

- [x] `evalstore.py`: schema, streaming ingest filtered to positions already in the book,
      and a read side that assembles the same `PositionEval` the engine produces.
- [x] `tools/ingest_evals.py`: streams `.jsonl`, `.jsonl.gz` or `.jsonl.zst` without
      unpacking, filtered against the book, same shape as `build_local_db.py`.
- [x] Sign convention detected from the data rather than assumed — see the note below.
- [x] `analyze()` consults the store first and runs the engine only on what is left; the
      store applies even under `--no-engine`, so statistics-only runs still get deep
      verdicts where the dataset reaches.
- [x] Optional throughout: no store, or a position it lacks, falls through to the engine.
      Git-ignored, never shipped in the repo.
- [x] 20 tests including both sign conventions, mate scores, malformed input and fall-through.
- [ ] Run the real ingest and record actual book coverage. Needs bandwidth and disk this
      sandbox does not have.
- [ ] Once coverage is known, reconsider the drill grader (`S4`): stored depth-40 lines are a
      far better teacher than a depth-12 search, and may remove the need for a live engine
      in the drill loop entirely.

### The sign convention note

The dataset's point of view is not clearly documented, and getting it backwards would invert
every verdict in the report with nothing failing loudly. So `detect_pov` works it out: in
positions with lopsided material, an evaluation from White's point of view tracks White's
material, while one from the mover's tracks the mover's. Level positions — which is most of
the opening — cast no vote, because that is exactly where the two conventions agree.
Everything is normalised to the mover's point of view, matching `engine._cp`.

---

## The product spec, and where each piece stands

Ten items, given as the target shape of the product. Mapped to what exists.

| # | Asked for | Status |
| --- | --- | --- |
| 1 | Explain *why* a move is bad, not just which move the engine prefers | **Done.** Every finding names the opponent's reply and what it wins: "Black replies Nxe5, winning a piece." |
| 2 | Every leak → Learn → Practice → Retest, with spaced repetition | Open. Drill queue exists; scheduling and retest do not. |
| 3 | "My Repertoire" as a visual tree with strong lines, weak lines and gaps | Partly. The tree is inferred (`repertoire.build_repertoire`) and gaps are found; it is not yet drawn or editable. |
| 4 | Four kinds of problem: objective / practical / knowledge gap / low confidence | **Done.** `classify()` decides; the dashboard colours each one. |
| 5 | "What are you not ready for?" with Learn / Practice / Ignore | Mostly. The section ships; the three actions do not. |
| 6 | Varied practice: best move, opponent's idea, continue the line, explain why, timed | Open. One mode today. |
| 7 | Track improvement: "you fixed this", before/after, weakness score over time | Open. Needs run history (Phase 6). |
| 8 | Let users commit to their own repertoire choice and stop re-flagging it | Open. The highest-value item left; needs the tree persisted. |
| 9 | Simplify the UI around Dashboard → My Repertoire → Fix Mistakes → Practice → Progress | Open. Sections are in that order but the navigation still mirrors the pipeline. |

### Item 4 — how the four kinds are decided

An engine drop outranks everything, including a thin sample: whether a move throws away a
piece is a property of the position, not of how often it has been played. The win-rate flags
are the opposite — they are claims about the player's *results*, so on thin evidence they are
downgraded to "worth watching" rather than asserted. Coverage gaps are their own kind:
nothing has gone wrong yet, and the response is preparation rather than correction.

### Item 1 — where the "why" comes from

The engine already searched the position after the played move in order to score it, and was
discarding that search's principal variation. That first move is the refutation — the reply
the player walked into — and comparing material across the two plies turns it into a sentence.
No extra search, and the precomputed store carries the same thing.

---

## Cross-cutting, do alongside

| Item | Finding | Note |
| --- | --- | --- |
| Keyboard-operable board, live regions for verdicts, chart text alternatives | `X3` | Squares carry `tabindex="-1"`; drill feedback is announced to nobody |
| Replace Unicode pieces with inline SVG | `X4` | Windows renders both colours from one outline font |
| Vendor Chart.js and the fonts locally | `X5` | The page claims "no network calls" while loading two CDNs |
| Lock CORS to localhost origins; rate limit; descriptive User-Agent | `X6` `C08` | Currently `allow_origins=["*"]` and no throttle anywhere |
| Lichess OAuth instead of pasting an API token into a form | `C05` | Teaches a habit users should not have |
| Consumer-readable error states; no shell commands in the UI | `C05` | |
| Privacy page: what is fetched, retention, deletion | `C08` | Table stakes for asking for an account name |
| Book banded by rating, selected from the player's own rating | `S3` | `moves.rating_sum` is populated and never read |

---

## Testing

Every analysis rule gets a unit test with fixed records, per the existing non-functional target.
Statistical changes are tested against hand-computed values, not golden files, so an intentional
change to the model is visible as an intentional change to the test.

Baseline before this work: **34 passed, 5 skipped** (skips need the LFS book or a local engine).
After Phase 0: **54 passed, 5 skipped**. After Phase 2: **62 passed, 5 skipped**. After Phase 1: **64 passed, 5 skipped**. After Phase 3: **77 passed, 5 skipped**. After Phase 3b: **97 passed, 5 skipped**. After the taxonomy and the "why": **106 passed, 5 skipped**.

The five skips cover the engine and the LFS opening book, neither of which is available in every
environment. Phase 0 was therefore also verified by hand against a book built from the sample
archive (`tools/build_local_db.py --pgn sample_pgns`), driving the real API and the real dashboard
in a browser, since the automated end-to-end tests that assert on flags are among the skipped.
