# V3.1 — learn an idea, use it, return to it

The four main destinations remain **Today, Explore, Repertoire and Progress**.
Explore gains local sections for Path, Openings, Puzzles and Games. Existing
opening URLs, course IDs, repertoire entries and learning records are retained.
The public website and daily-session foundations (#34 and #35) are now released.

## Review the experience

1. Open `/app/#explore/path`. The recommended micro-lesson is highlighted;
   every lesson remains available. Switch to Simple list for a plain route.
   The three opening courses expose all 17 existing chapters beside the path.
2. Start **Spot the double attack**. Select the piece, follow the legal-move
   arrow, inspect its attacks, then play the checked continuation. Completing
   guided teaching introduces a pattern; it does not award unassisted recall.
3. Choose **Try a related puzzle**. This opens a different position from the
   same theme. The full-width mobile board and the large desktop board use the
   established keyboard, touch, promotion and orientation controls.
4. Try a wrong legal move, request a hint, mark a piece, or reveal a solution.
   Supported attempts stay separate from first-attempt answers without help.
   A revealed solution is recorded as revealed. Mate-in-one tasks accept every
   legal mating move, including an alternative to the database's chosen move.
5. Pause, reload and resume. Exact learner decisions, opponent replies,
   assistance, orientation and teaching frames survive. Opening-course and
   daily-session checkpoints are separate and remain available.
6. Return on another day. Learned patterns have their own scheduled recall,
   accessible from Today, Repertoire, the path and the puzzle library. Positions
   answered with help also appear in the Revisit queue.
7. Open Progress. Results name the sample and period; weekly days count actual
   completed work. Four small milestones recognise a first idea, first puzzle,
   later-day independent recall and ten distinct positions. Stable evidence IDs
   prevent duplicate awards. There is no invented rating or mastery percentage.
8. Use the profile piece in the header to choose a nickname, avatar, guide,
   flexible 1–7-day weekly goal, green/walnut/slate/high-contrast board, quiet
   bubbles and reduced motion. Completed guided revisits count as work; reopening a recap does not add a day.
   Weekly boundaries use a stable IANA timezone;
   the daily puzzle changes at midnight UTC.
9. Games provides a clear entrance to the three existing annotated model games.
   Openings keeps the existing searchable 20-opening library and move explorer.

## Content and performance

**12 short micro-lessons and 150 tactical positions**, with 25 positions in each
of six themes: forks, pins, loose pieces, discovered attacks, back-rank mates and
basic mates. These are additional tactics activities, not extra opening courses.
The existing three opening courses still contain 17 chapters and 59 positions.

The fixed source subset is CC0 Lichess data. IDs, provenance and selection rules
are in [the content notes](../chess_opening_analyzer/content/README.md). The
compiler applies the opponent's setup move before presenting the task, checks
all legal transitions, derives factual arrows/circles, and retains all mating
alternatives. Normal puzzle play requires no live engine evaluation. Source
motif tags are not a personalised diagnosis or a playing-strength estimate.

Six packs load on demand (about 64–163 KB raw JSON each). A loaded pack remains
playable during a connection outage in the current tab. This does **not** claim
full offline application installation or durable cross-reload pack caching.
Public search pages, sitemap, privacy defaults and opt-in measurement are kept.
The new app routes remain under the existing noindex workspace.

## Learning persistence

Learning preference writes now use a durable, owner-scoped outbox. Checkpoints
coalesce per key; failed deliveries retry on next boot, focus, reconnect or a
subsequent write. An acknowledgement cannot remove a newer queued value.
Immutable attempts, enrolments, completed chapters and earned milestones retain
stable IDs. New mutable learning records use millisecond timestamps: the server
rejects an older checkpoint; unversioned legacy records still update one another.
For equal timestamps, the last accepted delivery wins. Device clock skew remains
a limitation of this policy; it is not collaborative editing.

Boot merges missing guest learning and newer local checkpoints before adopting
account state. Pending writes remain owned by their original account. State requests carry
an expected account owner; the server rejects a stale tab’s reads, imports and
writes after an account switch. The local store blocks writes into a working
copy owned by another account and reloads the old tab. Sign-out first flushes learning and requires a
successful logout; a failed connection leaves the working copy intact and gives
an explanation. Account deletion removes its queue. Existing non-learning
mirrors keep their established behaviour; this milestone does not introduce an
outbox for game reports or repertoire editing.

## Verification

- 226 Python tests passed, including 16 tests against real PostgreSQL and checks
  of every compiled puzzle transition, source interpretation and teaching frame.
- The complete browser regression runs in CI; 181 journeys cover both the
  established application and new learning, recovery and account-switch flows.
  Exact revision and results are recorded on the pull request.
- 48 axe WCAG A/AA screen-state scans passed across 360px, 390px and desktop,
  in light and dark themes (path, profile, library, puzzle, hint, recap, progress
  and games). Automated checks supplement visual and keyboard inspection.
- Board layouts checked at 360, 390, 768 and 1440px. Original lesson controls stay
  above the mobile navigation; puzzle boards remain full-width on small phones.
- The #34/#35 production releases have green CI, and the public home, daily
  session script and sitemap return HTTP 200 on `chessleaklab.co.uk`.

## Screenshots

| Experience | Desktop | Phone |
| --- | --- | --- |
| Learning path | [1440px](review/v3-path-1440.png) | [390px](review/v3-path-390.png) |
| Teaching arrows | [1440px](review/v3-pattern-1440.png) | [390px](review/v3-pattern-390.png) |
| Puzzle library | [1440px](review/v3-puzzles-1440.png) | [390px](review/v3-puzzles-390.png) |
| Daily puzzle hint | [1440px](review/v3-daily-1440.png) | [390px](review/v3-daily-390.png) |
| Profile and appearance | [1440px](review/v3-profile-1440.png) | [390px](review/v3-profile-390.png) |

Full bot games, new opponents, whole-game key-moment review, social features and
installable offline packs remain the later V3.2/V3.3 milestones. This draft is
the complete first learning-loop slice for review before those phases.
