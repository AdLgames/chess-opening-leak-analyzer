# V4.1 review — know what to play when the book ends

This first V4 slice makes the proposed positioning playable: a short Italian
decision session on the existing board, available before signup or game import.
It builds on PR #36; neither milestone is merged by this change.

## Try it

Open `/app/?plan=italian#today`, use the homepage's **Try the Italian plan**
button, or find the invitation in Today or Explore. Today, Explore, Repertoire
and Progress remain the four main destinations.

1. Explore two read-only teaching diagrams with arrows and circles.
2. **Get the king safe:** castle before choosing how to open the centre.
3. **Prepare the break:** choose c3 or Re1. Both are accepted, with different
   explanations and their actual resulting positions.
4. **Answer their strike:** after Black's ...d5, remove the pawn threatening
   the bishop. A routine castle can be explored with the concrete ...dxc4 reply.
5. **Fresh-position challenge:** use a different move order to recognise when
   d4 has support. No answer arrows or direct hint appear unless requested.
6. Review the session, optionally reflect, and save a compact Italian plan.

These are bounded, original teaching scenarios, with authored opponent replies.
They are not complete bot games or an arbitrary-position AI tutor. Legal choices
outside the exercise target get neutral feedback unless the scenario supplies a
verified tactical consequence. An exercise retry does not establish that the
move was a chess mistake. The named guides have new plan-specific reactions,
and can refer to a real previous completed attempt at the same scenario.

## Personal findings and honest evidence

The first supported personal handoff is deliberately narrow. The latest report
must be real rather than a sample, describe White, match the exact position
(including turn/castling/en-passant state), contain a legal played move outside
the accepted choices, include a positive integer occurrence count, and report
an evaluation drop of at least half a pawn. A matching finding starts with its
actual move, count and reported engine estimate, then puts that situation first.
The fresh challenge remains last. Missing, thin or unsupported evidence produces
the authored example invitation, rather than a fabricated diagnosis.

Reports provide aggregate position findings today, not the per-game opportunity
ledger required to establish transfer. **This milestone does not measure use of
the idea in later games.** The recap and Progress explicitly separate guided
practice, a fresh-position answer and game evidence that is not measured yet.
There is no rating-gain claim or all-purpose mastery percentage.

## Saving and integration

The session, per-decision outcomes, optional reflection and saved focus use a new
`learning:v2:italian-plans-v1:` namespace in the established local/account
transport. Attempts are immutable and checkpoints use the existing versioned,
owner-scoped queue. Hints, reveals and explored alternatives survive reload.
Only a fresh first try without direct help gets that description; replaying a
result does not submit it again. Content versions remain separate and older
records are preserved. No database migration is required.

An explicit Save action adds an idea note to Repertoire without changing saved
moves or existing recall schedules. The saved plan can become Today's focus;
the existing daily routine remains accessible and can be chosen instead. The
board controller and original explorer position are restored on exit. Existing
course checkpoints, puzzles, imports, exports and account data remain available.
When device storage is blocked, the session says it lasts in the tab only.

All input positions and their complete legal moves are packed with the content.
The scenarios run without live engine or position requests once the workspace
is loaded. This is not a claim that the full website is installable or works
offline from a cold start. The content file is approximately 60 KB before
compression; other puzzle packs retain their existing lazy loading.

## Verification

The release suite covers all legal input moves, accepted answers, opponent
replies and consequence positions. It verifies the asserted pawn/rook support,
the bishop threat and the distinct held-out challenge. Accepted teaching moves
were examined with Stockfish at depth 17 and have automated depth-16 checks
against the engine's alternatives. This checks the chess, not learning efficacy;
an expert review and user pilot remain necessary before expanding the curriculum.

Browser coverage exercises both preparations through real board controls,
keyboard play, consequence demonstrations, hidden challenge hints, exact resume,
reveals, immutable results, saved focus, existing daily/course transitions,
offline play, blocked storage, account queue retries and conservative personal
finding matches. Responsive and accessibility review covers phone, tablet and
desktop in light/dark. Exact-head release results are recorded in the PR.

| State | Desktop | Phone |
| --- | --- | --- |
| Explore invitation | [1440px](review/v4-explore-1440.png) | [360px](review/v4-explore-360.png) |
| Visual teaching | [1440px](review/v4-idea-1440.png) | [360px](review/v4-idea-360.png) |
| First decision | [1440px](review/v4-decision-1440.png) | [360px](review/v4-decision-360.png) |
| Concrete consequence | [1440px](review/v4-consequence-1440.png) | [360px](review/v4-consequence-360.png) |
| Fresh challenge | [1440px](review/v4-challenge-1440.png) | [360px](review/v4-challenge-360.png) |
| Recap | [1440px](review/v4-recap-1440.png) | [360px](review/v4-recap-360.png) |
| Saved plan | [1440px](review/v4-saved-plan-1440.png) | [360px](review/v4-saved-plan-360.png) |
| Practice evidence | [1440px](review/v4-progress-1440.png) | [360px](review/v4-progress-360.png) |

## Next gate

Run the small pilot described in [the V4 strategy](../chess-learning-v4-strategy.md).
Test whether existing opening-trainer users can complete the session, handle a
new position, and explain why they would return. Extend the reviewed scenarios
only after that feedback. Per-game source IDs, deduplicated eligible-opportunity
records and conservative concept matchers are the prerequisites for later-game
evidence; the current aggregate reports cannot substitute for them.

Content regeneration: `python chess_opening_analyzer/tools/build_italian_plans.py`.
The generator uses python-chess; the checked-in pack is what the browser runs.
