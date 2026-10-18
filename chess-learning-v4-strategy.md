# V4 — know what to play when the book ends

18 October 2026 · Research and proposed direction

The first authorised implementation slice is documented in the
[V4.1 review](docs/v4-italian-plans-review.md). Later slices below remain proposals.

## Recommendation

Build the opening-to-middlegame practice companion for players who remember
their opening moves but struggle when the opponent does something unexpected.

**Proposed promise: “Know what to play when the book ends.”**

The experience should connect one recurring decision from a player's games to
a short explanation, varied practical rehearsal and later game evidence.
Keep playing on Chess.com or Lichess; use Opening Leak Lab to prepare the next
decision. Start with adult rapid players around 1000–1600 on their chosen
platform who already use an opening trainer. This audience is a hypothesis;
ratings across platforms are not interchangeable.

This is a focused positioning and execution bet. Public research does not
establish an unoccupied category or a feature nobody else has.

## What the competition already offers

Reviewed first-party public pages on 18 October 2026. These establish advertised
capabilities, not independently tested quality, adoption or learning outcomes.
Do not use a competitor's comparison page as evidence about a third product.

| Product | Relevant advertised capabilities | Implication for us |
| --- | --- | --- |
| [ChessAtlas](https://chessatlas.net/features/deviation-finder) | Game import, deviations from a repertoire, gaps, trends and corrections routed into spaced review | Import → deviation → drill is already a direct competitive overlap. |
| [Chessbook](https://chessbook.com/) | Coverage, replies common at a player's level, spaced repetition, personal-game mistakes, middlegame plans and model-game guessing | “Relevant openings” and “understand the plan” alone do not separate us. |
| [Chessreps](https://www.chessreps.com/openings) | Opening courses and spaced repetition, with accessible, playful writing | A fun voice and more opening lines are insufficient positioning. |
| [Chess.com Game Review](https://support.chess.com/en/articles/8584089-how-does-game-review-work) | Move classifications, coach explanations, visualisations, retries and course recommendations | Characters, arrows and a retry button are useful delivery tools, already familiar elsewhere. |
| [Lichess](https://lichess.org/features) | Free analysis, studies, insights, opening explorers and learning from mistakes | Basic analysis and a lower price are weak reasons to switch. |
| [Aimchess](https://aimchess.com/) | Aggregate diagnostics and personalised exercises built from a player's games | Personalisation is an established category, not our exclusive invention. |
| [DecodeChess](https://decodechess.com/features/) | Explanations of engine moves, threats, plans and position concepts | Explaining “why” also has direct competitors. |
| [Ferzia](https://ferzia.com/personalized-chess-training) | Describes recurring concepts, varied drills and checking later games | Even the broad mistake → concept → practice → later evidence story already exists. |
| [Audit Chess](https://www.auditchess.com/) | Advertises personal mistake puzzles, off-book repertoire practice and missions with targets in later games | Human-like deviations and outcome tracking cannot honestly be advertised as exclusive either. |

The screenshot correctly identifies a crowded market. Our current four-tab UI,
coaches, library and training tools provide a foundation. A bigger checklist
does not yet give a player a compelling reason to use this product weekly.

## The experience to make exceptional

### 1. Practise the decision after the remembered line

Start at the point where a player needs a plan, including sound choices that
leave their repertoire. Leaving preparation is not automatically a mistake.

Each small, reviewed teaching unit contains a recognisable position, a question,
the important board relationship, a playable continuation and conditions where
the idea no longer works. For example, an Italian unit could ask whether the
central pawn break is ready or still needs preparation. Exact positions and
answers need chess-content review; a general slogan cannot grade every position.

Teach one useful decision rather than add ten more memorised plies by default.

### 2. Rehearse unexpected replies

Run short branching scenarios from the player's openings: a normal reply, an
awkward but playable deviation, and a changed position where the familiar plan
needs adapting. Reuse the same idea without replaying an identical move order.

Choose replies from a documented dataset or authored scenario. Only describe a
reply as common at a player's level when the relevant rating/time-control sample
actually supports that statement. Avoid random engine blunders dressed as a
human personality. Distinguish a sound alternative from failure to recall the
player's chosen repertoire move.

### 3. Make progress visible in later decisions

Keep three separate statements: recalled the prepared move, handled a fresh
practice position, and applied the idea in an imported game. None proves the
others. Only the last uses game evidence.

For narrowly supported concepts, show eligible opportunities and source games,
with dates and the matching rule. An illustrative display, not a user result:
“Before practice: 1 of 5 eligible positions. Since practice: 3 of 4.” Explain
that this is a small observational sample, not proof of a training effect.

No matching positions means “Not encountered in your imported games yet.” A
player who stopped choosing an opening has not necessarily improved at it.
Separate time controls, prevent duplicate games and keep sample/demo results
out of personal evidence. Do not infer broad concepts reliably from arbitrary
positions in the first release; start with reviewed, bounded matchers.

### 4. Give the guides a useful memory

Let Maya, Theo and Inez refer to actual learning history: “Last time we practised
preparing the break. What changes when this defender moves?” Ask before showing
the answer; animate the relevant threat after the attempt.

Use a short optional reflection such as “Forgot the line / Missed the threat /
Wasn't sure of the plan.” This is the player's report, not a diagnosis of their
thoughts. Tailor the next exercise when evidence supports it. Praise applying an
idea in a fresh situation as well as remembering a book move. Keep quiet mode.

Personal history, reviewed scenarios and clear feedback make the characters
useful. Additional costumes, quips or open-ended chat are not the core V4 bet.

## A concrete first visit

1. The board asks: “What do you do when they don't play your line?” Offer a
   playable demonstration before signup or import.
2. The player tries one decision. The guide shows one reason with arrows and
   circles, then changes the opponent's reply.
3. The player handles a fresh position and saves the idea. Invite them to bring
   games to find a relevant personal focus.
4. When imported evidence supports it, Today recommends one focus for upcoming
   games and explains why it was selected. With thin evidence, offer a chosen
   starter focus rather than invent a weakness.
5. A later import checks eligible decisions and adjusts the next session. The
   player can open the games behind every result and choose a different focus.

Keep the existing navigation: Today runs the next session; Explore offers
openings and ideas; Repertoire stores intended moves and compact plan notes;
Progress separates practice results from game evidence. No fifth dashboard or
collection of competing calls to action is necessary.

## Build and validate in small slices

| Slice | Deliverable | Acceptance condition |
| --- | --- | --- |
| V4 discovery | Observe existing trainer users handling unfamiliar replies; compare our demo against their current workflow | Identify a repeated unmet need and what they would replace or add us for. |
| V4.1 | One complete opening-to-plan unit with a guided personal finding, fresh-position challenge and saved focus | Works with a sample before import and with supported personal evidence after import; accepts reviewed alternatives and preserves saved work. |
| V4.2 | Short branching rehearsal with verified coach feedback and resumable sessions | The idea transfers to unseen authored positions; phone performance and both colours pass checks. Full bot matches are not required. |
| V4.3 | Conservative matching of later game opportunities and an understandable evidence view | Samples, exclusions and source games are inspectable; no opportunities, duplicates, changed repertoire and small samples behave honestly. |

Suggested pilot: 12–20 relevant players, including people who already use
Chessbook, ChessAtlas or comparable trainers. Observe a first session and follow
up over several weeks. Ask what was useful before describing our intended benefit.

For an initial 12-person usability cohort, proposed decision gates are: at least
8 complete the core session without assistance, at least 6 return during the
following week, and at least 6 choose it for this specific task over their
current workflow and can explain why. These are product decision thresholds,
not statistically validated learning-effect estimates. Record why people leave.

Measure time to the first useful decision, independent success on held-out
positions, repeat use and willingness to pay after experiencing the product.
For game transfer, report eligible opportunities and uncertainty; a later,
adequately sized comparison with a delayed-training group is needed before
making causal improvement claims. Do not promise Elo gains.

## What we already have, and what is missing

The V3.1 review branch already supplies the board, authored explanations,
visual teaching, recall, short engine practice, imported-report exercises and
account learning records. Personal exercises currently favour an exact saved or
engine response. That is a starting point, not a complete concept-transfer system.

V4 needs reviewed plan units, valid alternative answers, varied scenarios,
versioned concept/matching rules and per-game opportunity evidence. Keep source
game IDs, source timestamps, training cutoffs and matcher versions so imports
can be deduplicated and claims traced. Aggregate report changes alone cannot
prove that a player applied an idea. Existing opening-cost estimates are
prioritisation signals, not estimated rating points recoverable through training.

Complete import status and durable repertoire/report saving before claiming a
seamless cross-device personal coach. Reuse and validate V3.2's short scenarios
where they fit this direction. This strategy does not merge the current review
PR or authorise the entire remaining V3 backlog.

## Why people might choose it, and how that becomes durable

The reason to try it is a clear task: “I know the opening, but what now?” The
reason to return is the next relevant decision and visible evidence from the
player's own games. The combination must feel easier and more useful than
assembling several tools. This remains a hypothesis until the pilot supports it.

Reviewed branching lessons, accumulated user-controlled learning history and
reliable evidence can improve the product over time. A colour scheme or API
wrapper cannot provide that advantage on its own. Preserve PGN exports and
account deletion; convenience should earn retention rather than lock-in.

Test distribution with short board demonstrations and small opening-specific
creators or coaches. Future pages should answer concrete opening-to-plan
questions and launch a real exercise. Another generic “best chess trainer” page
is unlikely to communicate this value. No outreach is authorised by this plan.

Test willingness to pay for an ongoing personal programme after demonstrating
a complete useful cycle. Keep a useful sample available; assess engine costs
before deciding analysis limits. Research does not establish a price or viable
business model yet.

Defer more general bot personalities, a broad course-count race, social feeds,
leaderboards and an unrestricted AI chat assistant. V4 succeeds when players
choose this particular practice experience and make better-supported decisions
in fresh positions, rather than when the menu gets longer.
