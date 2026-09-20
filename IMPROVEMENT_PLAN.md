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
at 10% and the Philidor at 7%. The run-over-run comparison landed with item 7.

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

- [x] Run history stored with the player's other local state (SQLite beside the marks and the
      review schedule, rather than IndexedDB — it lives where the analysis runs, not in the page).
- [x] Per-finding deltas between runs: gone, new, better, worse — see item 7.
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
| 2 | Every leak → Learn → Practice → Retest, with spaced repetition | **Done.** `review.py` schedules by SM-2; misses return within the session and again the next day. |
| 3 | "My Repertoire" as a visual tree with strong lines, weak lines and gaps | **Done.** `repertoire.build_tree` draws the lines actually played, coloured by how each is doing, with unmet replies hanging off the move that reaches them. |
| 4 | Four kinds of problem: objective / practical / knowledge gap / low confidence | **Done.** `classify()` decides; the dashboard colours each one. |
| 5 | "What are you not ready for?" with Learn / Practice / Ignore | **Done.** All three, persisted in `gap_decisions`; Practise enrols against a book-derived answer, and ignored gaps stay gone across runs. |
| 6 | Varied practice: best move, opponent's idea, continue the line, explain why, timed | **Done.** All five: four modes plus a clock that applies to any of them, all feeding one schedule. |
| 7 | Track improvement: "you fixed this", before/after, weakness score over time | **Done.** `history.py` stores each run and diffs it per position: cleared, new, better, worse — and refuses to compare runs over very different game counts. |
| 8 | Let users commit to their own repertoire choice and stop re-flagging it | **Done.** `marks.py` records "this is my move" / "not interested"; committing drops the results argument and keeps the objective one. |
| 9 | Simplify the UI around Dashboard → My Repertoire → Fix Mistakes → Practice → Progress | **Done.** Five destinations; each shows only the sections that answer its question. |

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

## Item 8 — the player's own decisions

**Status: done**

A tool that keeps flagging a move you have deliberately chosen is a tool you stop believing.
`marks.py` records a decision against a position and side:

- **committed** — this is my move. The *results* argument is dropped: the win-rate comparison
  and the popularity complaint, both of which really say "most people prefer something else",
  and the player has already had that argument. What survives is the engine drop, because
  whether a move loses material is a fact about the position rather than a matter of taste.
  That is exactly the "unless they're objectively problematic" line.
- **ignored** — I have seen this and do not want it again. Silences everything.

A decision applies only to the move it was made about: switching to a different move is a new
choice and gets judged on its own. The two colours decide separately, since the same position
can be reached from either side. Both are undoable.

Kept in SQLite under `~/.local/share/leaklab/` — deliberately not under `~/.cache`, because a
cache is by definition something you can throw away and this is what the player told us. The
schema already carries a `user_id`, so accounts turn a constant into a real column and nothing
else changes.

Reached from the finding itself: *This is my move* / *Not interested* / *Undo my decision*,
with `GET`/`POST /api/repertoire` behind them and `--marks-db` / `--no-marks` on the CLI.

Verified end to end: committing to a move with `WINRATE_DECLINE+EVAL_DROP` leaves
`EVAL_DROP` alone and the finding explains why it is still listed; committing to a
win-rate-only finding removes it; ignoring removes one outright; and a decision about
2.Nf3 after 1.e4 e5 correctly leaves 2.Nf3 in the Sicilian alone, because the key is the
position rather than the move's name.

---

## Item 2 — Learn, practise, retest

**Status: done**

One graded attempt is a quiz. Remembering an opening comes from recalling the same line
days later, and again after that. Two clocks run, and conflating them would break both:

- **Within the session.** A position just missed returns a few places later — far enough
  that the answer is off the screen, near enough to be the same sitting. That repetition is
  what makes it stick at all. Mirrored on both sides (`review.requeue_within_session` and
  the same function in `study.js`) so the queue behaves identically wherever it is driven.
- **Across days.** SM-2: an ease factor per position that rises with easy recall and falls
  without it, multiplying the gap each time — one day, then six, then longer.

Two deliberate departures from textbook SM-2, both about not insulting the player:

- A lapse comes back tomorrow rather than resetting to a fresh card. They have met this line
  before; the job is to repair it, not to pretend otherwise. The ease carries over, so
  repeated lapses still shorten future gaps.
- Asking to be shown the answer is always a lapse, however good the move would have been.
  Recognising a move is not recalling it.

Grades come from the same centipawn thresholds the practice pane already displays, so what
the player is told and what the schedule believes never disagree.

State lives in the same SQLite file as the repertoire decisions. Enrolling is idempotent, so
re-running the analysis re-offers the same positions without wiping progress — the failure
mode that would quietly undo weeks of work.

Verified in the browser: eight positions enrolled and due, revealing an answer requeued that
position from first to fourth, "due today" fell 8 → 7, and the stored schedule showed ease
2.5 → 1.96 with a lapse and a due date of tomorrow. The reveal path records the lapse even
when the engine is unavailable, since the player has already said they could not recall it.

---

## Item 3 — the repertoire, drawn

**Status: done**

Every decision already carries the move list that reached it, so the tree is simply the trie
of those lines: nothing re-derived, and the opponent's moves fall out as the edges between
the player's own. Each of the player's edges carries its record, so the shape of the
repertoire and how it is doing are the same picture.

Four states, one colour apart: **strong** (good results over enough games), **weak** (flagged
in the report), **committed** (their decision — never shown as weak, because saying so over
the top of a choice is the arguing-back the marks exist to stop), and **played**, which is
everything else. Unmet replies hang off the move that reaches them as "+n unmet".

Drawn as an indented list rather than a graph. That is a deliberate choice: it stays readable
on a phone, it is navigable by keyboard for nothing, it survives a long line without panning,
and the shape of the trunk is what matters rather than the geometry. An opponent edge inherits
the weight of everything below it, so the trunk reads as the trunk instead of as whichever
leaf happens to be biggest.

Verified in the browser against the demo archive: as Black, `1.d4 Nf6` reads green at 58% while
`1.d4 d5` reads red at 14% with its whole branch below it, opponent moves stay grey as
structure, and the side switch redraws both trees.

### The bug this shipped with, briefly

Gaps attached to nothing: a gap's line is written with move numbers (`1.e4 c6 2.Nc3`) and a
node's is not (`e4 c6`), so the two never matched and every repertoire reported zero gaps. Both
are now reduced to bare SAN, and the gap's own reply is dropped before matching, since a gap
hangs off the player's move that *reaches* the position. An older test had encoded the wrong
assumption and has been corrected rather than deleted.

---

## Item 9 — five destinations

**Status: done**

The sidebar listed eleven sections in the order the analysis computes them, which is the
pipeline's order rather than anyone's. It is now the five the spec named: **Dashboard**,
**My repertoire**, **Fix mistakes**, **Practice**, **Progress**.

The sections themselves are unchanged — each destination simply shows the ones that answer
its question, so nobody scrolls past a chart to reach the thing they came for:

| Destination | Shows |
| --- | --- |
| Dashboard | run · overview · where the points go |
| My repertoire | the tree · what you're not ready for · openings library |
| Fix mistakes | fix list · leak table · the board |
| Practice | the drill queue |
| Progress | how the fixes are bedding in · engine and data |

A section still hides itself when it has nothing to say; the view only decides which are
*eligible*, so the two conditions never fight. Section numbering is gone, since these are
no longer a sequence. And a finished run now lands on **Fix mistakes** rather than leaving
the reader on the form that started it.

Progress is a new destination rather than a new subsystem: the review schedule already knew
known / still learning / due / recall accuracy, and this asks it. It re-reads on arrival,
because those numbers move every time a drill is answered and a page-load snapshot would go
stale within one session — which is exactly what the first version did, showing "nothing
tracked yet" beside eight tracked positions.

---

## Item 6 — four ways to be asked

**Status: done**

One drill mode teaches one thing: recall of a move you have already been shown. That is
worth having, but it is not the same skill as understanding *why* the move is wrong, and a
player who can produce `Bc5` on cue may still walk into `Ng5` next week without seeing it
coming.

Practice now has four modes, chosen above the board, plus a clock that applies to any of them:

| Mode | The question | Graded against |
| --- | --- | --- |
| Find the move | You played `Nf6` here and scored 31%. Find something better. | the engine's pick, with partial credit |
| Find the punishment | Take the other side, after `Nf6`. Show why it does not work. | the refutation |
| Play the line | Play the improvement and keep going; the opponent answers from the book. | staying in book for four moves |
| Explain why | Before looking: what does your opponent get out of this? | the player's own honest answer |

**Find the punishment** is close to free: the refutation is already captured from the child
search's principal variation during analysis, which the engine used to discard. The board
flips, the mistake is played, and the position the player keeps walking into is the one they
are asked to solve — with no engine call at answer time.

**Play the line** exists because knowing the one better move is not the same as knowing the
line, and a club repertoire usually runs out two moves later. The opponent replies with the
book's *most common* answer rather than the engine's best: preparation has to survive
ordinary opposition, not perfect opposition. Going out of book is not scored as a blunder —
it says what the book plays instead, and where the book itself runs out it says that too,
which is worth knowing.

**Explain why** has no move to grade, so the player grades themselves — the standard answer
in spaced repetition for recall a machine cannot mark. It is the one mode with no clock: the
honest answer to "did you already know this" is not improved by rushing it.

**The clock** is a modifier rather than a fifth tab, because timed is not a different
question — it is the same question under pressure. Running out counts as a miss, deliberately:
a move you cannot find in thirty seconds is not one you have yet, and scoring it any other way
makes the schedule optimistic about what the player knows.

Every mode feeds the same schedule. A missed punishment, an abandoned line and an honest "no,
that is new" are lapses like any other — they are four views of one weakness, not four
separate curricula.

---

## Item 7 — did any of this work?

**Status: done**

A report says what is wrong today. Two reports say whether last month's work did anything,
which is the only question that brings anyone back. Each run is now stored — its headline
figures and its flagged decisions — and Progress opens with the comparison in one sentence:

> One of your leaks is gone since last time, worth about 6.5 points. Nothing new appeared.

Beneath it, the two lists that sentence summarises: cleared, and new.

Three things this deliberately does *not* do:

- **Report aggregate movement.** "Lost points down 6.5" is satisfying and nearly meaningless,
  because it moves with the number of games read. The diff is per position, keyed on
  `(epd, colour, move)` — so `2.Nf3` in the Sicilian and `2.Nf3` in the King's Pawn are two
  different leaks, as they should be.
- **Call variance a trend.** A line's cost must move by 20% before it counts as better or
  worse; without that, every run looks like it moved.
- **Compare runs it should not.** A leak that vanished because it was fixed and one that
  vanished because this run read forty games instead of two hundred look identical from the
  diff alone. So the game counts travel with the comparison, and when they differ by more than
  a third the headline says so instead of claiming progress:
  *"This run read 40 games and the last read 200, which is too different to compare fairly."*

History is a nicety, never a blocker — a failure to record a run is logged and the run
completes regardless.

---

## Cross-cutting: the page that phoned home

**Status: done**

The dashboard's whole claim is that nothing leaves the machine — it says so in the
sidebar, under "Network: not required". It then loaded two stylesheets from
`fonts.googleapis.com` and 200KB of Chart.js from `cdn.jsdelivr.net`, telling both a
third party the IP address of everyone who opened it.

- **Fonts** are vendored from npm (`@fontsource/*`, SIL OFL 1.1), latin subset, only the
  weights the stylesheet asks for: 176KB in `public/vendor/`.
- **Chart.js is gone rather than vendored.** The page drew two bar charts with it, which
  does not justify 200KB, and a `<canvas>` cannot be read by a screen reader. Both are
  now inline SVG in `public/charts.js` — under 200 lines — each with a real table of the
  same numbers collapsed beneath it, hover and keyboard-focus tooltips, and a
  `ResizeObserver` redraw (a chart drawn while its section was hidden measured zero).

Verified in Chromium: a full run from the demo archive completes with **zero requests
off-origin and zero console errors**.

The chart colours were run through a contrast and colour-vision-deficiency validator
rather than picked by eye. The original pair failed twice — `#79a9c9` sat outside the
lightness band and under the chroma floor against this surface, reading as grey — and is
now `#4f9ad4` against `#e06a5f`, which clears CVD separation at ΔE 17.3 (protan). The
single-series amber moved from the UI accent `#e3a44b` to `#bd7f28` for the same reason.

Two label defects the render caught, which no unit test would have:

- Rotated column labels ran down-and-right from their tick, drifting away from the
  column they name. They now rotate the other way and anchor at their end.
- Truncation kept the *head* of an opening name, so "King's Knight Opening: Normal
  Variation" and "King's Knight Opening: Konstantinopolsky" became the same label on two
  different bars. It now keeps the distinguishing tail.

---

## Cross-cutting: who may call the API  ·  `X6` `C08`

**Status: done**

The server binds `0.0.0.0` and answered `allow_origins=["*"]` with no throttle anywhere.
On one laptop that is nearly harmless; on a shared network it means any page the user has
open in another tab can read their game history off the port, and any script can queue
unbounded analysis jobs.

`chessopening/guard.py` holds both pieces, outside the server module so they can be
tested without standing a server up:

| | Now | Escape hatch |
| --- | --- | --- |
| Origins | localhost on the dev ports, plus `null` so the file:// path still works | `LEAKLAB_ORIGINS`, including `*` for anyone who genuinely wants the old behaviour |
| Analysis runs | 20/hour — each spawns an engine and reads an archive | `LEAKLAB_ANALYZE_PER_HOUR` |
| Reads | 600/minute — the dashboard polls these freely | `LEAKLAB_READS_PER_MINUTE` |

`X-Forwarded-For` is ignored unless `LEAKLAB_TRUST_PROXY=1`: it is a header the caller
sets, so honouring it by default would let anyone mint a fresh budget per request. The
limiter is deliberately in-process and fixed-window — it bounds accidents, not
adversaries, and the docstring says so rather than implying more.

Verified against the running server: an allowed origin is echoed, `https://evil.example`
gets no CORS header at all, and the sixth read against a limit of five returns
`429` with `Retry-After: 59` and *"That is a lot of requests at once. Try again in 59
seconds."*

Separately, the outbound `User-Agent` in `explorer.py` was
`chess-opening-analyzer/1.0 (+https://github.com/)` — a link to nothing, which is worse
than sending no URL. Both fetchers now share the one definition in `ingest.py`.

And `LEAKLAB_BOOK` now overrides the bundled book path, because the shipped file is a Git
LFS pointer until it is pulled and swapping in a differently-built book should not mean
editing the package.

---

## Item 5 — three things to do about a gap

**Status: done**

"What are you not ready for" listed the replies and then offered one action: a link to
lichess.org — a strange answer from a tool whose whole pitch is that it works offline, and
no help at all in deciding what to *do*. The spec asked for Learn, Practice and Ignore.

**Ignore** is the one that makes the section trustworthy. A list that only ever grows is a
list people stop opening; somebody who does not play into the French does not need to be
told about it every month. The decision persists in `gap_decisions` and is applied
server-side on the next run — verified by ignoring `1.e4 e6`, re-running from scratch, and
watching it stay gone.

**Learn** opens the position on the board that is already in the page, with the local book
and engine behind it, and marks the gap as being worked on.

**Practice** enrols it in the review cycle. That needed something the report did not have:
a gap is a position the player has *never faced*, so there is no move of theirs to grade
against. `best_reply()` takes the target from the book instead — and getting that right
took two goes:

> Shrinkage alone does not do it. A 12-game 100% line shrinks to about 71% against a prior
> of 50, which still beats a 1000-game 64% mainline, so the player would have been drilled
> on a curiosity. A candidate now needs a real *share* of the position's games as well —
> which is also the more honest rule: the answer to "what do I play here" ought to be
> something real opponents have had to meet.

Where the book is too thin to name an answer, Practise is disabled and says why, rather
than enrolling the player in a drill with no correct move.

Rendering it caught a labelling bug that had nothing to do with this feature: gaps were
named after the position *before* the reply, so `1.e4 c6` was captioned "King's Pawn Game"
while the board underneath correctly said Caro-Kann. Gaps are now named by where the reply
lands.

---

## Cross-cutting: the board, for people not using a mouse  ·  `X3` `X4`

**Status: done**

The board was a grid of `div`s with `role="button"`, `tabindex="-1"` and no accessible
name — sixty-four unnamed buttons, none of them reachable. Verdicts appeared silently.
And the pieces were Unicode glyphs.

**The pieces.** A glyph came from whichever system font happened to have one — on Windows
that is Segoe UI Symbol, which draws them as monochrome *outlines*. Colouring an outline
glyph white leaves a white piece as a white outline: on a light square, invisible. They are
now inline SVG: filled shapes with a contrasting stroke, depending on no installed font and
legible at 22px as well as 60px. The artwork is original, drawn for this board — the
obvious free set (Cburnett) is on npm under a relicence that does not clearly cover the
artwork, and that is not a call to make quietly inside a commit.

**The keyboard.** The board is now a `role="grid"` with a roving tabindex — one tab stop,
not sixty-four. Arrow keys move a cursor, Enter selects and moves, Escape deselects,
Home/End jump along the rank. Arrows follow the *screen*, not the board, so they do not
invert when you play as Black. The cursor is deliberately separate from the selection:
moving over a square is not picking the piece up, exactly as with a mouse. Mouse and
keyboard both route through one `activate()`, so the two cannot drift apart.

**The names.** Each square reads as "f 8, black bishop" — and carries the state the
colours carry: ", selected", ", can move here", ", can capture here". Without that last
part a keyboard player has no idea which squares are legal, which is the entire thing the
dots convey to everyone else.

**The verdicts.** Drill feedback, the drill prompt and task, the review status and the book
summary are all `aria-live="polite"` regions. A verdict that only appears visually is a
verdict half the audience never receives.

Verified in Chromium by playing a move end to end with no mouse at all: focus the board,
arrow to f8, Enter (label becomes "f 8, black bishop, selected", c5 becomes "c 5, empty,
can move here"), arrow to c5, Enter — move played, verdict announced.

The charts' half of `X3` was done with the charts: both carry a real table of their numbers,
and every bar is focusable with its own label.

---

## Cross-cutting: errors people can act on, and a straight answer about data  ·  `C05` `C08`

**Status: done**

### The error messages

The analyzer began as a command-line tool, where this is exactly the right thing to print:

> Stockfish not found. Bundle a local copy with `python tools/install_stockfish.py`, or
> install it system-wide (apt install stockfish / brew install stockfish), or pass
> --engine /path/to/stockfish, or set STOCKFISH_PATH.

That sentence went straight into the browser, in front of somebody who wanted to know why
their openings leak points and is now reading about environment variables. `messages.py`
translates: a headline, one sentence about what still works, and the original text kept
under "What the program reported" for whoever does want the command. Nothing is hidden — it
is just not the first thing, and a bug report is better for still having it.

> **No chess engine on this computer.** Everything based on your results still works —
> which openings cost you points, how you score against the database, all of the practice.
> What you lose is the engine's verdict on individual moves.

It is a small table rather than anything clever, and the fallback is an honest "Something
went wrong" rather than a confident wrong guess. There is a test asserting no shell command
reaches a headline or a detail, and another asserting every branch keeps the raw text.

### The 500 this uncovered

`/api/meta` returned a **500** whenever the opening book was a Git LFS pointer that had not
been pulled — which is the state of every fresh clone. The whole page failed over a file
that had simply not downloaded yet. Both `db_info()` and `board_db()` now catch it: the
first reports it as a missing book with the explanation above, the second returns `None` so
the board still draws and the engine still runs, with only the book panel empty.

### What happens to your data

Anything that asks for a username owes the reader this, in plain words. A sheet off the
sidebar now says where the analysis happens (here), what leaves the machine and when (a
request to Lichess or Chess.com containing the username you typed, and nothing at all if
you upload a PGN), what is kept and where — including *why* the decisions live in
`~/.local/share` and not the cache folder — how to delete it (two folders; there is no
server holding a copy), and who else can reach the local API.

---

## Rating bands: comparing you with players like you  ·  `S3`

**Status: done, and it needs a rebuilt book to show**

The book folds every game together, so "the database scores 54% here" really means
"everyone from 800 to 2800 scores 54% here". Those are different games. A line that is
excellent once both sides know the theory can be a poor practical choice at 1400; a line
that scores well at 1400 *because* it is easy to meet badly may be nothing at master level.
Telling a 1400 they are 6% below a number set largely by players two classes above them is
not a useful thing to tell them.

**A correction to this plan.** The original entry said `moves.rating_sum` was "populated and
never read". Only the second half was true — the builder never wrote it, so the column was
zeros. Both halves are now done: the builder records it, and the book carries per-band rows.

| | |
| --- | --- |
| Bands | under 1200 · 1200–1600 · 1600–2000 · 2000–2400 · 2400+ |
| Written | every game counts twice — into its own band and into `all` — so one book answers both questions with no join |
| The player's rating | the **median** across their own games; a mean is dragged around by one game against somebody far stronger, and by a provisional rating early in an archive |
| Too thin to use | widens *outward* to the neighbouring bands, then to everybody |

Bands are coarse deliberately. Narrow bands cut the games behind each move, and the whole
analysis rests on having enough of them: a comparison against exactly the right population
with eight games behind it is worse than one against a slightly wrong population with eight
hundred. For the same reason the widening goes outward one band at a time rather than
jumping straight to everyone, and `baseline_band` records per row which population was
actually used — because after widening it is not always the player's own.

**Old books keep working, untouched.** The shipped book has no `band` column at all, so the
query itself changes shape rather than filtering on a column that is not there. The file is
never altered to add one: it is the player's file, and opening it should not rewrite it.
There is a test asserting exactly that.

The dashboard now says who you were measured against instead of leaving it to be assumed:

> Compared against players rated 1600–2000, since your games put you around 1754.

…and, on a book without bands, says that too rather than quietly comparing against everyone:

> Compared against every rating together — this opening book has no rating bands.
> Rebuilding it compares you with players at your own strength.

**What this needs from the maintainer:** the shipped 157k-game book predates the column, so
the banded comparison only starts working once it is rebuilt with
`python tools/build_local_db.py`. Until then everything behaves exactly as before and the
page says so.

---

## Cross-cutting, do alongside

| Item | Finding | Note |
| --- | --- | --- |
| Lichess OAuth instead of pasting an API token into a form | `C05` | Teaches a habit users should not have |

---

## Testing

Every analysis rule gets a unit test with fixed records, per the existing non-functional target.
Statistical changes are tested against hand-computed values, not golden files, so an intentional
change to the model is visible as an intentional change to the test.

Baseline before this work: **34 passed, 5 skipped** (skips need the LFS book or a local engine).
After Phase 0: **54 passed, 5 skipped**. After Phase 2: **62 passed, 5 skipped**. After Phase 1: **64 passed, 5 skipped**. After Phase 3: **77 passed, 5 skipped**. After Phase 3b: **97 passed, 5 skipped**. After the taxonomy and the "why": **106 passed, 5 skipped**. After repertoire decisions: **119 passed, 5 skipped**. After spaced repetition: **147 passed, 5 skipped**. After the repertoire tree: **159 passed, 5 skipped**. After run-over-run comparison and the second practice mode: **173 passed, 5 skipped**. After locking down the API: **190 passed, 5 skipped**. After the gap actions: **205 passed, 5 skipped**. After the error translation: **216 passed, 5 skipped**. After rating bands: **232 passed, 5 skipped**.

The five skips cover the engine and the LFS opening book, neither of which is available in every
environment.

### Against the real book: 237 passed, nothing skipped

CI only fires on pushes to `main` and on pull requests, so nothing had ever run on this
branch. A manual dispatch against it settles both of the open questions:

- **All five skipped tests ran and passed** — Stockfish 17.1 and the real 157,625-game book
  (three months of rated Lichess, elo 1500–2100). **237 passed, 0 skipped.**
- **Flag calibration against the real book is confirmed.** The demo archive produces 24
  flagged rows there rather than the 8 a 900-game toy book gives, and the sentences hold up
  on real data:

  > You played 6.Nc3 9 times and scored 11%. Black replies **Bxc3+**, winning a piece.
  > **Qxd4** keeps the position in hand — 6.1 pawns better than what you played. Based on
  > few games so far, so treat it as a hint rather than a verdict.

  Every part of Phase 0 and Phase 1 is visible in that one line: the shrunk baseline, the
  confidence hedge on nine games, the refutation, and the material consequence in words.

- The run also confirms the banding fallback in production conditions: *"This opening book
  has no rating bands, so the comparison is against all ratings together. Rebuilding it adds
  them."* Phase 0 was therefore also verified by hand against a book built from the sample
archive (`tools/build_local_db.py --pgn sample_pgns`), driving the real API and the real dashboard
in a browser, since the automated end-to-end tests that assert on flags are among the skipped.
