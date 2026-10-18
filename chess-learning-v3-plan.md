# V3 — a chess companion you want to come back to

18 October 2026 · Proposed roadmap · Planning only

## Product direction

**Learn an idea → try it in a position → play with it → understand the key moment → remember it later.**

V3 should make that journey feel connected, substantial and personal. The board
remains the centre of play and teaching. Characters supply warmth and useful
feedback; the path makes the next step obvious; puzzles and practice games give
the ideas somewhere to go.

The four supplied Chess.com screenshots suggest four useful patterns: a playful
learning journey, a home with clear activities, a reason to revisit through
progress and achievements, and a deeper library of things to learn or watch.
Use those patterns with our own layout, illustrations, characters and writing.

## Starting point: what is already here

PRs #34 and #35 were released on 18 October before implementing V3.1.
The daily-session and public-site foundations are now live. The first V3
implementation is documented in [the review guide](docs/v3-learning-journey-review.md).
Later phases below remain a roadmap, rather than shipped capabilities.

| Existing capability | V3 should evolve it into |
| --- | --- |
| Today, Explore, Repertoire, Progress | A coherent home for courses, puzzles and coached practice without losing saved lines |
| Three authored courses, 17 chapters, 59 positions | A visible learning journey plus additional reviewed content |
| Maya, Theo and Inez; speech bubbles, quiet mode | More expressive coaching with context-specific teaching interactions |
| 177 arrow/circle teaching frames in #34 | Interactive questions, comparison lines and demonstrations of threats |
| Recall schedules and resumable 5/10/15-minute sessions in #34 | A routine mixing due recall, an idea and relevant application |
| Five learner moves against Stockfish | Longer, optional coached practice and complete bot games |
| Model games and personal-game preparation | A board-led key-moment review linked back to training |
| Local learning records and an account mirror | Reliable queued writes and tested conflict/recovery behaviour |
| Public course/guide pages and SEO in #35 | Useful search entry points into each real learning activity |

Arrows, speech bubbles, daily planning, game import, opening exploration and
basic recall are not new v3 features. The additions below build on them.

## What to take from Chess.com

Chess.com documents both a guided lesson path and a searchable library. Our
equivalent should combine a recommended route with freedom to browse, rather
than force every player through the same sequence. [Lessons documentation](https://support.chess.com/en/articles/8609703-how-do-lessons-work-on-chess-com).

| Feature family | Our version | Delivery |
| --- | --- | --- |
| Learning path | Illustrated chapter journey with one highlighted next lesson and a plain-list alternative | V3.1 |
| Daily and themed puzzles | A daily position, six tactical themes and a queue of positions to revisit | V3.1 |
| Coach-led play | Help during a practice game, threat explanations, takebacks and a useful recap | V3.2 |
| Bot personalities | Three original opponents with demonstrably different practice scenarios/styles | V3.2 |
| Game review | A few useful decisions explained on the board, followed by Retry and Save for review | V3.2 |
| Stats and skills | Development, king safety, tactics and opening recall with actual samples and dates | V3.1–2 |
| Awards and goals | Weekly training goal, earned milestones and a small collection of meaningful achievements | V3.1 |
| Profile and themes | Own avatar, favourite guide, board/piece presets and private learning history | V3.1 |
| Watch, videos and events | Annotated game of the week, guess-the-move moments, curated external viewing links | V3.3 |
| Friends | Opt-in challenge links and small shared goals | V3.3 |
| Messages and clubs | Separate future community project once reporting, blocking and moderation are operational | Later |
| Rated online matches, tournaments and leaderboards | Separate multiplayer project with clocks, reconnects, matchmaking and fair-play operations | Later |
| Membership | Consider advanced content/analysis after cost and repeat-use evidence; no subscription implementation in the core v3 release | Later |

The wider comparison uses Chess.com’s [feature overview](https://www.chess.com/article/view/chesscom-features),
[puzzle modes](https://support.chess.com/en/articles/8608686-how-do-puzzles-work-on-chess-com),
[achievements](https://support.chess.com/en/articles/8618496-what-are-achievements)
and [profile/settings options](https://support.chess.com/en/articles/8615285-how-do-i-manage-my-settings).
These are design references, not requirements to reproduce every feature.

## Screen and interaction plan

### Today: one useful invitation, several reasons to return

Keep the main Start/Resume session action and the board. Display the next lesson
or review, its purpose and the approximate duration. Under it, add a compact
weekly goal and two clear shortcuts: Daily puzzle and Play with your coach.
Show the last genuinely earned milestone when relevant, rather than empty
statistic cards for a new user.

An example invitation: “Your next idea: spot a fork. Review two positions, learn
the pattern, then try it.” Task counts come from the real queue. Returning users
resume the saved activity instead of being sent to a fresh lesson.

### Explore: a substantial library with a recommended path

Keep the four existing main destinations. Add local sections within Explore:
Path, Openings, Puzzles and Games. Courses remain searchable, and the existing
opening search and move explorer remain directly accessible. Play is available
from Today and from a studied position. Profile, awards, themes, support and
settings sit in the profile menu.

This avoids turning the mobile footer into a crowded list of every activity.
If actual usability tests show that Play deserves a fifth destination, prototype
and test that change before replacing navigation or breaking existing links.

The path should use original illustrated landmarks, a visible route and a
character near the next lesson. Each node represents real available content:
Learn → Try → Recall later → Apply. Use distinct “introduced”, “review due” and
“recalled without help” states. A completed reading step is not proof of mastery.
Keep the complete chapter list available; recommendation does not mean a hard
lock. Support reduced motion and a simple list view of the same content.

### The board and coach: explain one relationship at a time

Extend the current diagrams into active questions: “Which squares does this
knight attack?”, “Which piece is undefended?”, “What did that move threaten?”
and “Which development move helps the centre?” The player should do something
before the explanation, not just click through another text panel.

Allow a short comparison: play the candidate move, show the reply, then return
to the original exercise. Display no more arrows/circles than needed for the
current idea. Explain geometric attacks separately from legal moves, especially
for pinned pieces, kings and pawns. Each interaction has an equivalent text or
keyboard action.

Give each existing guide six useful expressions/poses: explaining, thinking,
pointing, celebrating, surprised and reassuring. Keep the guide recognisable
across lessons, puzzles, review and practice. Characters can peek from the frame
and gesture towards a target, while leaving pieces, controls and touch targets
clear. Bubbles remain dismissible; essential instructions stay available.

Write jokes around verified events. For the existing Nxf7 fork, for example:
“One knight. Two very nervous pieces.” Follow with the actual queen/rook targets.
For a legal repertoire alternative: “Legal move. Different plan. Let’s compare.”
Changing the guide changes the voice, not the chess verdict.

Optional spoken explanations belong after the visual/text experience works.
Make voice opt-in, cancellable and accompanied by the text; prototype device
support before promising a consistent voice on all phones.

### Puzzles: useful tactics connected to the repertoire

Launch with a proposed **150-position curated starter pack** across six themes:
forks, pins, hanging pieces, discovered attacks, back-rank patterns and basic
mates. Include a daily puzzle, choose-a-theme practice and a revisit queue.
Provide a short authored explanation for the showcased daily/tutorial examples.
The 150 positions and six themes are content targets, not content already built.

Prefer early-game examples and positions related to the player’s selected
openings when enough reviewed material exists. If a matching opening is not
available, offer a clearly labelled general tactical puzzle. Give the choice
of another theme rather than inventing personalised relevance.

Use a curated subset of the [Lichess CC0 puzzle database](https://database.lichess.org/#puzzles).
Its source FEN precedes the opponent’s first listed move: apply that move before
presenting the decision. Validate every solution transition, side to move and
promotion. Accept alternative mating moves in mate-in-one tasks. Store source
IDs and content versions; load small packs rather than a huge database on phones.

Start untimed. Hints reveal a clue, then a marked square, then a move only when
requested. Helped attempts and later unhinted success remain separate. Add an
optional short timed challenge only after ordinary puzzle play and review work.

### Play: a character with a purpose

First extend the current short practice into a 10-move coached scenario with
pause/resume, hints and takebacks. Then support complete unrated bot games,
including resignation, draws, promotion and PGN export. Let people begin from
the starting position, a course position or a saved repertoire position.

Propose three original opponent roles: an early attacker, a patient builder and
a tactical opportunist. Start with reviewed scenario branches and calibrated
engine settings. A chat personality alone does not establish a playing style,
and a weakened engine should not be marketed as having a verified human rating.
Use descriptive challenge levels until calibration supports stronger claims.

The selected guide can explain a relevant threat after a move, offer a clue or
demonstrate a consequence. Undo restores the exact position and preserves an
honest assistance record. After the game, choose a small number of teachable
moments and offer a related lesson or saved review position.

These ideas draw on [Play Coach](https://support.chess.com/en/articles/10877257-how-do-i-play-against-the-coach)
and [bot practice](https://support.chess.com/en/articles/8614091-how-can-i-play-against-the-chess-com-bots).
Our implementation should start with a few well-tested opponents, not a large
gallery of superficially different characters.

### Review and Progress: connect evidence to the next action

Evolve existing personal preparation into a board-led review of **up to three
useful moments** per analysed game: a prepared response missed, an important
threat, or an opportunity worth practising. Show What happened → Why it matters
→ Try again → Save for review. Demonstrate the opponent’s reply and retain
the original game and move number.

Keep engine findings, repertoire mismatch and authored advice distinct. Engine
verdicts must include the relevant position, search limits and continuation.
When analysis is unavailable, keep the game browsable without inventing a grade.
Replay and saved exercises extend the work already built; a complete replica of
Chess.com’s whole-game review is not required for the first v3 release.
Reference: [Chess.com Game Review](https://support.chess.com/en/articles/8584089-how-does-game-review-work).

Progress should explain what changed with actual observations: “6 of 8 fork
positions solved first time without help in the last 30 days.” Keep opening
coverage, delayed recall, puzzle results and game evidence separate. Topic tags
can guide practice without suggesting that eight puzzles measure all of tactics.
Imported playing ratings must name the provider, time control and last update;
our participation rewards are not a playing rating.

### Goals, achievements, profile and appearance

Add a flexible weekly goal, such as three training days, and a small activity
calendar. Recognise a first chapter, a first later-day recall, ten different
positions practised and a first completed coached scenario. Reward eligible work
once. Replaying a solved position, refreshing a recap or retrying a sync request
must not duplicate XP. Define XP as participation, with no purchased recovery or
loss of earned learning when someone misses a day.

Provide an avatar and nickname, favourite guide and preferred training duration.
Launch with three board/piece presets and an accessible high-contrast option.
Keep colour-independent selection, target and hint indicators. Dark/light and
motion settings remain compatible with existing preferences. Make learning
history private by default; sharing is a deliberate action.

### Games, viewing and a little community

Expand the current model-game feature into a game-of-the-week experience: short
context, playable board, three guess-the-move pauses and one takeaway linked to
a course. Add sourced external video/event links when relevant. A small editorial
selection is feasible before a constantly updated news/broadcast service.
Chess.com’s [event hub](https://support.chess.com/en/articles/8709013-how-can-i-see-events-and-tournaments)
is an inspiration for discovery, not a dependency or a content feed we own.

Later, let friends share a daily challenge or a selected public repertoire
snapshot. Include expiry/revocation where relevant, and make the shared material
explicit. Private game archives and notes do not become public because a profile
exists. Direct messages and public clubs wait for operating tools and staffing.

An installable web app is a useful v3.3 extension. Downloadable offline packs
require local legal-move validation and tested sync; the current offline public
preview does not mean the complete app already works offline.

## Delivery sequence and review gates

| Release | Concrete scope | Review gate |
| --- | --- | --- |
| Foundation | Review/release #34–35; verify persistence, queued writes, stable content IDs and timezone rules; prototype path and engine options | Existing records survive upgrade, offline writes retry without duplication, no fresh login resets checkpoints |
| V3.1 — Learn and return | Path for existing courses; 12 proposed foundation/tactical micro-lessons; curated daily/theme puzzles; weekly goal, initial milestones, profile/theme controls and coach expression updates | New user finishes an idea and a relevant puzzle; returning user resumes, recalls later and earns the right milestone once |
| V3.2 — Play and understand | Three scenario opponents; 10-move coached practice; complete bot games after engine gate; key-moment review and evidence-based topic progress | Both colours, undo/resume and terminal positions work; game review creates a valid, non-duplicated exercise |
| V3.3 — Discover and share | Game of the week, selected viewing links, opt-in friend challenges, optional timed puzzle mode and installable web experience | Shared snapshots are explicit; optional features work without breaking private learning or slowing public pages |

Expand authored opening content after the first complete learning loop is proven.
A proposed next set is London System, Alapin against the Sicilian and French
Advance for White, subject to chess review and demand. Aim for **six courses and
roughly 150–200 authored positions**, not hundreds of database labels presented
as full courses. This still would not be exhaustive coverage of every reply.

Do not set a calendar promise from feature count alone. Size the engine and sync
work first, and include design, original artwork and human chess-content review
in the estimate. Review each release as a complete working slice before starting
the next.

## Technical work that makes the product trustworthy

- Preserve existing `learning:v2` attempts, course IDs, checkpoints and saved
  repertoire entries. A path references those records instead of replacing them.
  Version new puzzle/scenario content and back up any required migrations.
- Extend the existing learning model with content/skill tags, puzzle attempts,
  goal periods, idempotent reward events and saved practice games. Keep helped,
  first-attempt and later-day recall outcomes distinct.
- Replace the current account mirror’s known limitations with a durable outbox
  and a defined conflict policy before promising seamless offline or multi-device
  progress. Test sign-in import, sign-out, retry and concurrent edits.
- Keep normal lessons/puzzles independent of live engine evaluation. Author and
  validate their solutions and teaching frames ahead of time.
- For sustained bot games, benchmark a single-thread Stockfish WebAssembly worker
  against supported iPhone/Android devices. Check memory, loading, cancellation
  and battery behaviour, and provide the appropriate licence/source distribution.
  Keep a bounded server fallback only if cost/latency measurements support it.
  Existing server request limits cannot simply be assumed sufficient for full games.
- Record factual explanation inputs separately from character text. Unsupported
  positions get a limited explanation or a labelled engine line, not confident
  generated positional advice.
- Continue the existing stack unless a focused prototype shows a clear reason
  to change it. Keep public pages static/crawlable and load play/engine assets
  only when needed. Publish source/licence notes for new content and artwork.

## First implementation milestone

**A player follows a visible course path, learns one tactical idea with their
guide, solves a related puzzle and returns to review it.**

1. Prototype Today, the path, a puzzle and its recap at 360px and desktop.
2. Define node/content IDs, assisted outcomes, goal/reward eligibility and sync
   behaviour against representative existing accounts before changing records.
3. Build the existing courses into the path and author the first micro-lesson.
4. Compile the curated puzzle pack, including first-move FEN handling and all
   accepted solutions; deliver the daily puzzle and theme selector.
5. Connect a small number of context-appropriate coach reactions, a weekly goal
   and genuine earned milestones. Keep a reduced-motion/list alternative.
6. Complete the whole learning/resume/review loop and deliver a review preview.

Full bot matches, social messaging, broadcasts and billing are separate from this
first milestone. They remain visible on the roadmap without shipping empty menu
items or distracting placeholder pages.

## Release and learning checks

- Test both colours, keyboard/touch, promotion, castling, en passant, mate,
  stalemate and the applicable repetition/move-count draw rules in complete games.
- Verify wrong-answer retry, hints, reveal, takeback, precise resume, stale engine
  replies, API/engine failure and content-version changes without losing progress.
- Exercise duplicate reward submissions, offline sync, simultaneous devices,
  timezone/week boundaries, existing account import and deletion/export.
- Check 360/390px phones, tablet and desktop, enlarged text, high contrast,
  reduced motion, meaningful board labels and bubbles that leave moves reachable.
- Keep public search pages fast, preserve URLs and link new real courses and
  teaching guides into the existing sitemap. Avoid publishing thin placeholder
  pages merely because new path nodes are planned.
- With the existing opt-in measurement model, observe first-session completion,
  later-day return, independent delayed recall and completion of related practice.
  Establish the baseline before choosing numeric growth targets. XP totals and
  bot wins alone are not evidence of chess improvement.

No application functionality, deployment, subscriptions or account data was
changed in producing this roadmap.
