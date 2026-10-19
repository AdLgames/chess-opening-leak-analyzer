# Deep opening library and decision review

This change builds on draft PR #37 (`feat/v4-italian-plans`). It keeps Today,
Explore, Repertoire and Progress as the four primary destinations. No saved data
is migrated or removed, and no earlier draft is merged.

## Try the library

Open `/app/#explore/lines`, or choose **Deep opening library** within Explore.
The catalogue works without signup or game import. Browse familiar opening
families, sort by longest route or ECO code, search names/codes/move sequences,
filter by first move, and save routes for later.

Choose **Walk through** to return to the main study board. **Deep lines** is a
keyboard-accessible tab beside Study and Moves. Step forward/back, jump to any
reference move, use the normal board controls, or explicitly start/pause the
runthrough. Compare named branches and sample-game frequencies at every position.
A named-branch link filters the catalogue to routes through that exact position.
Play any legal move to leave the reference sequence; **Reference start** restores
it. Navigation, training and a hidden browser tab stop autoplay. Stale network
responses cannot take control from a newly started lesson.

### What the data covers

- Complete pinned snapshot of the CC0 [Lichess chess-openings dataset](https://github.com/lichess-org/chess-openings/tree/a6189a30dc273ccb21fc2536a9a2fefd5592a67a):
  **3,865 named routes, all 500 ECO codes, 7,983 exact positions**, through at most
  **36 plies / 18 full moves**. Major routes and sidelines are included.
- Every SAN/coordinate move is replayed and validated with python-chess. Forks
  merge by exact position, including side to move, castling and legal en-passant
  state; transpositions share alternatives.
- Sources, CC0 dedication, checksums and an offline deterministic builder are in
  `chess_opening_analyzer/content/openings/` and
  `chess_opening_analyzer/tools/build_opening_lines.py`.
- The generated static data totals about **3.3 MB uncompressed**. The 632 KB index
  loads only when requested; one ECO pack and relevant position shards load on
  demand. It is not loaded on the initial Today screen.
- These are named reference routes, **not every possible chess continuation or
  3,865 authored courses**. Existing opening introductions and courses remain.
  End of a reference entry does not mean end of opening theory.
- Observed game frequencies come from the independently installed statistics
  book. Its metadata is displayed; the bundled book currently contains 157,625
  games, built through move 15, with its original filters. No book was replaced.
  “Most played in sample” describes frequency, not move quality or theoretical
  priority. The old 40-reply query limit was removed to preserve all recorded
  replies and the complete frequency denominator. All legal continuations remain
  available where the sample or named reference runs out.

## Try the decision review

Open Progress and **Understand the decision**. With a report, expand a flagged
position to see reproducible board context and the report's first engine
alternative. Show the resulting position on the main board with a verified
capture arrow/circle and a guide explanation; compare continuations or create
an existing personal practice exercise for the legal report response. Explore
that opening's routes directly from the review.

Choose a learning focus and optionally record what you remember: forgotten line,
missed threat, unclear plan, felt short of time, experiment or uncertainty. Notes
are limited to 280 characters. Today suggests a displayed decision using the
chosen focus and recorded reflections, then unreviewed report findings. The
review shows distinct position/move records, counts the displayed reflections
and keeps recall-attempt history separate. It currently shows the first 20
unique flagged decisions from the latest report; the original full report
remains available in Game analysis.

A fresh analysis records source game/ply/date and PGN clocks when present. Elapsed
time comes from explicit `%emt`, or successive clocks for the same player plus
a known simple increment. First/missing/invalid clocks and unsupported staged
time controls do not manufacture elapsed time. Lichess exports now request
clocks and use a separate cache name. Generic Site tags such as “Chess.com” no
longer collapse unrelated source records; exported game links are preferred.
Source counts are deduplicated within the latest report, not accumulated over
repeated imports. Detailed evidence is bounded to 120 flagged rows and the first
eight source examples per decision, with total counts retained.

Older saved reports still work: board context is calculated on demand, while
missing clock/source evidence says to run a fresh analysis. Sample-game evidence
is visibly labelled and its reflections are stored separately from personal
reflections. A legal capture is not asserted to win material. Clock readings,
practice results and user reflections do not establish psychological causes or
improvement in later games. That longitudinal measurement remains a later step.

## Arrows and saving

The shared board renderer now draws an actual closed triangular head for every
straight or bent arrow. It no longer references repeated document-wide SVG
marker IDs, so a hidden review/preview/drill board cannot steal another board's
head. Both orientations and the existing colours/outlines/circles remain.

Bookmarks use `learning:v2:opening-lines-v1:bookmark:*`; goals and reflections
use `learning:v2:decision-lab-v1:*`. They use the existing local/account transport,
backup and owner-scoped retry queue. Mutable writes have monotonically increasing
versions and removals use tombstones. Original lines, notes, courses, schedules,
reports and progress remain intact. Cached game-ID restoration also accepts the
existing saved camel-case field. Storage failure messages distinguish the tab's
working copy from persistent storage.

## Validation and visual review

The local Python suite passes **233 tests**; its **16 PostgreSQL integration
tests** run against the CI database. The targeted new browser suite passes
**12 journeys**, covering exact full-depth board replay, forks, search, bookmarks,
reflections, personal practice, missing/source clock evidence, account retries,
delayed responses and arrows in both orientations. The CLI successfully analysed
83 sample games with real Stockfish at depth 10.

The full browser suite and exact-head hosted/CI release checks are tracked in
the draft pull request. Their final results are recorded in its check runs. An axe WCAG 2 A/AA + 2.1 AA audit covers 48 combinations:
six new states at 360, 390, 768 and 1440 pixels, in light and dark themes.
No violations or horizontal overflow were found. Screenshots below use a labelled
synthetic sample report to demonstrate decision review, not a real user's data.

- [Catalogue, desktop](review/deep-catalogue-1440.png) and [phone](review/deep-catalogue-390.png).
- [Runthrough, desktop](review/deep-runthrough-1440.png) and [phone](review/deep-runthrough-390.png).
- [Deep-position controls, phone](review/deep-runthrough-controls-390.png).
- [Decision review, desktop](review/deep-decision-review-1440.png) and [reflection, phone](review/deep-reflection-390.png).
- [Capture arrow, desktop](review/deep-capture-arrow-1440.png) and [phone](review/deep-capture-arrow-390.png).
