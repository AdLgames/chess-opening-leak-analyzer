# Chess learning platform — product and build plan

17 October 2026 · Proposed direction · Working name retained until the core experience is validated

## 1. The product we are building

**A beautiful chess workspace that turns an opening database into a repertoire you understand, remember and use.**

The user should always be able to answer: What should I learn next? Why does it matter? Am I getting better?

The proposed differentiator is **visible preparedness**: show the important replies a repertoire covers, explain the gaps, and turn those gaps into a manageable training programme. Personal games make that programme more relevant, but are optional. This is a positioning hypothesis to test, not a claim of exclusive functionality.

Start with improving club and online players who know the rules and want reliable openings. Assume roughly 900–1800 online rating for initial content design, recognising that ratings differ between platforms. Validate this audience in the first design sprint. Do not attempt beginner chess instruction, professional preparation and a comprehensive game archive in the same first release.

**The first-session promise:** choose an opening, understand one useful idea, play a short lesson and leave with something saved to practise again. Target less than three minutes to the first meaningful training interaction, without importing games or creating an account.

**The repeat-use promise:** open the app, press one button, complete a useful 5–15 minute session, and know what improved.

## 2. Product principles and scope guardrails

1. One obvious next action per screen. Additional tools are available in context.
2. The board is the centre of study. Navigation, statistics and rewards support it.
3. Explain before exposing numbers. Show “Learn the common response to …c5” before an engine table.
4. Make the default useful. No mandatory PGN import, rating questionnaire or advanced settings.
5. Reveal complexity gradually. Browsing an opening must be simple; editing variations may be powerful.
6. Separate covered, remembered and demonstrated in games. Never compress these into a misleading mastery percentage.
7. Reward learning and returning. Do not make missed days feel like losing progress.
8. Preserve user work. Autosave, undo, import previews and resumable sessions are part of the core product.
9. Teach ideas as well as moves. Each starter chapter needs a plan, a common deviation and a useful follow-up position.
10. Finish one complete experience before adding more modes or social features.

The MVP excludes a course marketplace, social feed, public leaderboards, currencies, subscriptions, opponent scouting, unlimited engine analysis and automated instructional chat. Keep existing analysis available as a secondary tool. Leave the name and monetisation decisions until the product is useful.

## 3. Four destinations, one training experience

| Destination | Primary job | Main action | Secondary content |
| --- | --- | --- | --- |
| Today | Know what to do now | Start today's session | Weekly goal, current chapter, session length |
| Explore | Discover openings and investigate positions | Try a lesson / add to repertoire | Move statistics, variations, examples |
| Repertoire | Organise what I intend to play | Continue learning / practise | White and Black lines, gaps, notes, import/export |
| Progress | Understand improvement | Review next focus | Recall, coverage, consistency, optional game evidence |

Desktop uses a compact left sidebar. Mobile uses a four-item labelled bottom navigation. Account, appearance, help and game connections live behind the profile menu. Personal game findings can also appear in Today when actionable.

Training is a focused session entered from Today, an opening or a repertoire chapter. It does not need a fifth navigation tab. It remembers where the user came from and returns there on exit.

Use ordinary labels: “Explore”, “Learn”, “Practise”, “Your lines”, “Common replies”, “Review tomorrow”. Avoid product-facing labels such as clinic, leak severity, cost index, EPD, cohort or engine tolerance.

## 4. Screen specifications

### A. First visit: make a useful choice, then play

Show three entry choices: “Help me choose”, “I know my opening” and a quieter “Import a PGN”. The recommended route asks only which side the player wants to learn, with an optional broad experience choice. Offer a small curated selection and a clear “Not sure? Try this” recommendation. Explain each opening in one sentence about its typical positions and plans.

Let the user play a sample lesson before asking them to save an account. At completion, explain that guest progress is saved on this device and offer sign-in for backup and sync. Session length can be adjusted on Today; no need to collect it in an onboarding form.

Acceptance: a new user can start from no games and no saved repertoire; back navigation preserves choices; skipping account creation does not discard the lesson; importing is never presented as mandatory.

### B. Today: a training invitation

Above the fold, show a warm greeting, one large session card and a compact weekly goal. Example content:

> Your next step: get comfortable against the Advance Variation.
>
> About 10 minutes · 5 reviews · 1 new idea · 1 practical challenge
>
> **Start session**

Below it, show “Continue your repertoire” with at most two active cards. Each shows its current chapter and a simple readiness description. Keep achievements and historical graphs out of the hero area.

Session length uses a small 5 / 10 / 15 minute control. The estimated task count updates before starting. If no reviews are due, offer a new lesson or light practice; do not invent a review backlog. If many are due, provide a manageable session and a reassuring catch-up option.

Acceptance: the main action is visible on a typical phone without scrolling; returning users can resume in one tap; a brand-new account has a meaningful state rather than zero-filled charts.

### C. Explore: a friendly entrance to a serious database

The default view has search, White/Black filters and opening-family cards. Search supports names, ECO codes and pasted moves; offer position/FEN search through an advanced control. Cards show the opening name, short purpose, side and whether guided content is available. Clearly distinguish named openings in the database from authored lessons.

An opening detail view contains a playable board, a short explanation of the plan, chapter list, and “Try first lesson” or “Add to repertoire”. A consistent subnavigation separates **Learn** from **Explore moves**.

In the move explorer, use the board on the left and one active panel on the right: Moves, Ideas or Games. Move rows show notation, frequency and a compact results bar. Show sample count and dataset scope; explain that results are observations, not proof that one move is best. Rating and time-control filters appear only where supported by the dataset. Empty results should offer a broader filter or another line.

Engine output is an expandable tool, not the headline. Saving a variation should be available beside the move list and preserve the path the user explored.

Acceptance: explore without an analysis run; follow and undo moves; choose a variation; save it and find it immediately in Repertoire. Unsupported filters are absent. A position outside the book gets a useful empty state, not fabricated statistics.

### D. Repertoire: a personal collection with clear gaps

Default to clean cards organised under White and Black. Each card shows the opening, current chapter, due reviews and the next meaningful gap. Opening a card reveals a chapter list. The full variation tree is an optional editing view; it is not the first screen a casual user sees.

Use a vertical chapter journey: Essentials → Common replies → Typical plans → Practical test. Show human-readable states: New, Learning, Review due and Remembered. Learning content remains freely browsable; progression recommends an order without locking users out.

The editor supports playing moves to add branches, selecting preferred responses, notes, replacing a move, undo and PGN import/export. Import presents a preview: side, chapters, variations and any parsing problems. It never silently overwrites an existing repertoire.

Represent gaps as useful invitations: “Prepare for 3…Bc5”, with why it is prioritised and a clear action. Offer one or two recommendations at a time rather than a wall of red warnings.

Acceptance: user-chosen moves survive reload and sync; independent repertoires do not overwrite each other; transpositions share appropriate learning history; changing a preferred response clearly updates affected training; deleting a chapter is reversible.

### E. Training: board first, teaching in small steps

Desktop: board takes most of the available space; a narrow side panel contains the prompt and explanation. Mobile: board fits the viewport width; a short prompt sits above it and feedback/actions below it. Avoid requiring scrolling between a move and its feedback.

Always show side to move, task instruction, session progress, Hint and Exit. Support tap-to-select and tap-to-move as well as dragging. Highlight legal destinations; include explicit promotion selection, board orientation and keyboard/screen-reader alternatives.

The session follows a predictable rhythm: brief prompt → user action → specific feedback → next task. Correct moves get a subtle confirmation. Mistakes preserve the position, give a small clue and allow retry. Reveal the answer only when requested or after a clear guided step. A revealed or hinted answer must not count as independent recall.

Distinguish “A sound move, but not your chosen repertoire move” from a chess mistake. Teach the saved choice without claiming all alternatives are bad. Never grade an unavailable engine result as correct.

When the lesson ends, show what the user practised, one improvement and when to return. One primary button: “Done for today”. Optional further practice stays secondary.

Acceptance: leaving and returning resumes safely; wrong answers reappear later without an endless retry loop; hints reduce recall credit; network failures preserve the current attempt; closing the session never demands completion to save progress.

### F. Progress: useful evidence, not a statistics dashboard

Lead with a plain-language weekly summary. Under it show three separate measures:

| Measure | Meaning | Safeguard |
| --- | --- | --- |
| Coverage | How much of the selected opening scope has a prepared response | Display scope, depth, dataset and confidence |
| Recall | How reliably due positions are answered without help | Show sample size and observation window |
| In games | Whether prepared responses appear in imported games | Optional; never infer from drills alone |

Consistency is a small weekly activity strip. Highlight a useful next focus. Avoid claims such as “you gained 80 Elo” or “this opening is 92% mastered”. An account with little data should say “Keep practising to build a reliable picture”.

## 5. Visual system and interaction quality

Direction: modern chess club meets polished learning app. Calm surfaces, excellent typography, attractive boards and restrained celebratory details.

| Element | Proposed design rule |
| --- | --- |
| Palette | Warm off-white canvas, dark ink text, deep green primary action, muted gold milestones |
| Board | High-contrast cream/green squares and clearly distinguishable classic pieces |
| Type | Legible sans serif for UI; tabular numerals for stats; consistent move notation |
| Spacing | 8px-based system; generous space around the board and primary actions |
| Controls | Aim for 44–48px touch targets; labelled icons; visible focus states |
| Motion | Brief move/feedback transitions; respect reduced-motion preferences |
| Colour meaning | Green success, amber learning/help, red actionable error; always add text/icons |
| Density | Simple defaults; reveal move trees, filters and engine detail on demand |
| Themes | Ship one polished theme first; add dark mode after shared tokens are stable |

Create reusable components before extending screens: app shell, board container, primary/secondary buttons, opening card, chapter row, move row, results bar, feedback panel, session header, progress indicator, empty state, inline error and undo notification.

Define loading, empty, error, saving and offline states alongside the happy path. Avoid full-page loading after every move. Reserve space to prevent layout jumps. Display “Saved” only after the relevant local or remote write succeeds; show pending sync separately.

Accessibility release checks include keyboard navigation, meaningful board announcements, contrast, 200% zoom, reduced motion, screen-reader form labels, and layouts at 360px phone width, tablet and desktop. Use an accessible move-entry/list alternative where spatial board navigation would otherwise block participation.

## 6. Gamification: progress worth earning

Keep only three game elements visible in normal use: **session XP, a flexible weekly goal and the chapter journey**. Achievements live on Progress. Do not put badges, coins, leagues and multiple progress meters on every screen.

| Mechanic | Behaviour | Purpose |
| --- | --- | --- |
| XP | Earned for useful learning events; one session total at the end | Immediate acknowledgement |
| Weekly goal | User chooses a realistic number of training days; can change it | Sustainable consistency |
| Chapter journey | Essentials, common replies, plans and practical test | Visible direction and completion |
| Milestones | First chapter, successful delayed recall, first week goal | Recognise meaningful progress |
| Personal bests | Compare with the user's own previous performance | Motivation without public ranking |

Initial XP rules are product parameters to tune: +10 for a scheduled independent recall, +5 for completing guided learning of a new position, and +15 for a first successful chapter checkpoint. Award once per eligible item/window; later retries of the same task do not farm XP. A helped answer earns learning completion where appropriate, but no independent-recall award. Use stable event IDs so reloads and sync retries cannot duplicate rewards.

XP measures participation, not playing strength. Do not use labels such as Master, IM or GM as level rewards. Opening knowledge and recall are calculated from training evidence independently of XP.

Use a weekly goal as the primary habit mechanic. A consecutive-day streak may be added later as an optional display, with no loss of earned knowledge or rewards when broken. Avoid countdown pressure, guilt copy, paid streak recovery and mandatory notifications.

Milestone celebration should last a moment and leave the next action clear. Sound is optional and off by default. Speed challenges can be a later voluntary mode; never make speed the default measure of understanding.

Example completion: “Session complete. You remembered 5 of 6 reviewed positions and learned the plan against …c5. 65 XP · 2 of 3 training days this week.” Use actual event data, not canned progress claims.

## 7. Training programme and content model

Build an adjustable daily queue from reviews first, then a small amount of new material, then an application task if available. Use estimated task durations to respect the chosen time budget. The session may be shorter if meaningful work is exhausted.

For a typical 10-minute session, aim initially for roughly half the time on due reviews, one-third on new material and the remainder on an idea or application exercise. These are starting heuristics, not rigid quotas. Pause new learning when review load is high and let the user override it.

Four task types share one interface:

1. **Learn a line:** guided moves and concise explanations.
2. **Recall a response:** an unhinted repertoire decision, with varied entry points and move orders where valid.
3. **Understand the idea:** choose a plan, identify a threat or make the thematic move; use authored feedback.
4. **Apply it:** play a short curated continuation from the resulting position. Open-ended engine sparring follows after the core release.

Review data includes first-answer correctness, hint/reveal use, response time, last attempt and next due time. Begin with a deterministic, tested scheduler and configurable intervals; calibrate from observed recall. A miss reappears after intervening tasks and receives a short future interval. Cap retries and offer a guided close so a session cannot trap the learner.

For a delayed checkpoint, sample multiple positions from a chapter without hints. Keep guided completion separate from remembered status. Do not label a chapter remembered solely because a user just repeated the answer.

Launch content should be small and excellent. Proposed pilot set: one Italian repertoire for White, one Caro-Kann repertoire against 1.e4, and one Queen's Gambit Declined repertoire against 1.d4. Have a qualified chess reviewer confirm suitability and missing move-order coverage before committing. Label the Black repertoires by their scope; neither alone is a complete answer to all White openings.

Each pilot repertoire needs a reviewed scope, essential lines, common alternatives, one or more thematic positions, model-game references where permitted, and a checkpoint. Expansion to flank openings and additional systems follows measured demand.

Every lesson stores source/provenance, author/reviewer, version and review status. Engine checks validate legal lines and obvious tactical claims; human review validates the explanation and teaching sequence. Database move frequency does not automatically become instructional content.

## 8. The database and preparedness feature

The existing opening book is a strong foundation for aggregated move exploration. It is not equivalent to a searchable archive of complete games. Keep three data products explicit:

| Layer | Contains | Delivery |
| --- | --- | --- |
| Opening explorer | Positions, legal transitions, frequencies, results and names | Core release, building on existing code |
| Learning library | Authored chapters, explanations, repertoire choices and exercises | Core release, curated pilot set |
| Full game database | Complete PGNs, player/event/date/result metadata and position index | Separate expansion after core validation |

Preparedness should answer a bounded question: “Within this repertoire, to the selected depth, which common opponent branches have an answer?” Rank gaps using estimated encounter frequency, absence of a chosen response and relevance to the learner. Add personal-game evidence only after opt-in import. Show the reason for each recommendation.

Use a transposition-aware position graph. Preserve side to move, castling rights and relevant en-passant information when identifying positions. Keep move histories for teaching and PGN export even when positions merge. A line tree is a view of the underlying graph.

Calculate probability-weighted coverage only where the data supports it. Define the opening scope, depth, chosen player moves and opponent response distribution. Stop or mark uncertainty outside the book; deduplicate converging positions and handle cycles explicitly. Do not treat one response at the starting position as full repertoire coverage. Keep the current personal-game coverage metric distinct during migration.

For the later full game database, store source identifiers, complete games, deduplication hashes and position-to-game references. Add player, event, date, result and position search, then a replay viewer. Dataset acquisition, reuse rights, refresh cadence, storage size and query performance require a separate technical spike. Show game examples only when the actual records are available.

## 9. Implementation approach grounded in the repository

The repository review covered the README, existing requirements/improvement-plan outlines and selected frontend/database source. It was a static review; runtime behaviour, deployment and the actual bundled database were not validated. Existing planning checkboxes may be stale and must not substitute for an inventory.

| Existing area | Keep or evolve |
| --- | --- |
| `chess-dashboard/public/app/app.js` and `index.html` | Replace report-first navigation/gating with the four-destination shell |
| `board.js` | Reuse legal-move interactions; audit touch, accessibility and error handling |
| `study.js` | Separate session orchestration, task grading and lesson presentation |
| `repertoire.js`, `prep.js` | Unify saved variations and chapter-oriented repertoire editing |
| `store.js` | Preserve existing state; migrate review records and reward events safely |
| `explorer.js` | Separate general database exploration from personal opening diagnostics |
| `chessopening/localdb.py`, `board.py`, `bands.py` | Retain book access, legal chess operations and supported dataset filtering |
| Existing analysis and ingestion | Feed optional recommendations; remove dependency from core learning |
| `vercel/accounts/*` | Audit and extend existing account/state support before introducing new storage |
| Local and hosted API entry points | Share business logic and contract tests to prevent behaviour drift |

Do not start with a framework rewrite. First establish components, explicit state boundaries and the complete learning flow in the existing stack. Introduce a framework only if a short technical spike identifies a concrete delivery or maintainability benefit worth the migration.

Logical records: repertoire, chapter, position, repertoire move, lesson version, exercise, attempt, review schedule, session, goal and reward event. Separate shared chess/content records from per-user progress. Version changes must not silently corrupt learning history.

Guest use is local-first. Signed-in users receive durable sync. Import guest progress explicitly at sign-in using stable IDs and a merge policy; repeated sign-in must not duplicate records. Preserve a migration backup and version old state. Prefer append-only attempts and reward events with idempotent writes; resolve edits using a defined version/conflict strategy.

Normal lessons and saved-response recall must not wait for live Stockfish. Use reviewed answers and known legal transitions. Optional analysis and deeper personal-game processing can run separately. Profile hosting constraints before expanding engine workloads or moving services.

## 10. Delivery plan and release gates

Planning range: roughly **10–14 calendar weeks** for a polished core beta with one experienced full-stack engineer plus regular part-time design and chess-content review. This is an estimate, not a commitment. Audit, data access and content readiness can change it. A full game archive is additional scope, initially estimate 3–5 weeks after a sizing spike. Do not trade the release gates for a date.

| Phase | Indicative window | Deliverables | Exit gate |
| --- | --- | --- | --- |
| 0. Validate and design | Week 1 | Running inventory, scope, four-screen prototype, design tokens, content outline | Five target users try the main flow; confusing labels and dead ends resolved |
| 1. App foundation | Weeks 2–3 | New shell, independent Explore access, guest onboarding, state migration, board polish | New user starts a lesson without importing games; existing user work survives upgrade |
| 2. Complete learning flow | Weeks 4–6 | One reviewed repertoire, chapter editor, lesson session, recall queue, save/resume | Explore → save → learn → delayed review → progress works end to end |
| 3. Preparedness and rewards | Weeks 7–8 | Gap prioritisation, daily plan, XP events, weekly goal, chapter milestones | Reasons and coverage scope are visible; reward duplication and inflated recall tests pass |
| 4. Content and hardening | Weeks 9–10 | Remaining pilot repertoires, sync verification, mobile/accessibility pass, error states | Content review complete; phone and desktop journeys pass; no known data-loss defects |
| 5. Pilot and refinement | Weeks 11–14 as needed | Cohort feedback, onboarding/queue adjustments, performance work, optional game feedback | Usability and retention evidence justify wider release |

The first meaningful demo arrives in phase 1. The first feature-complete learning slice arrives in phase 2. Resist spreading incomplete features across all three starter repertoires before that slice is proven.

### First sprint: concrete tickets

| ID | Ticket | Acceptance |
| --- | --- | --- |
| UX-01 | Map existing journeys and state | Inventory names actual gates, records and API dependencies; separates shipped behaviour from old plan claims |
| UX-02 | Prototype Today, Explore, chapter detail and training | Five representative tasks can be completed in the prototype without moderator explanation |
| UI-01 | Introduce design tokens and shared controls | Buttons, typography, cards, feedback and focus states are consistent across the four screens |
| NAV-01 | Implement four-destination shell | Direct links, back button and mobile bottom navigation work; training returns to origin |
| DB-01 | Open explorer independently | Clean browser can browse and play moves before any analysis run |
| REP-01 | Save an explored line | Saved side, move order, name and notes persist and reopen correctly |
| DATA-01 | Add versioned state migration | Representative old local/account states migrate without losing saved lines or attempts |
| CONTENT-01 | Author the first small chapter | Legal moves, explanations, alternatives, sources and reviewer sign-off are recorded |
| TRAIN-01 | Deliver the first guided session | Start, move, hint, retry, exit and resume work on touch and desktop |
| MEASURE-01 | Add minimal product events | Start/completion/abandonment and task outcomes can be measured without logging private PGN content |

Order: audit and prototype first; shell and data migration next; independent exploration and saved lines next; first guided session last. Content preparation can overlap implementation once the chapter format is agreed.

## 11. Quality, usability and learning validation

Use task-based testing with 5–8 target users at prototype, working slice and beta stages. Include phone users and people unfamiliar with repertoire tools. Ask them to choose an opening, save a line, complete a session, find a gap and resume later. Observe rather than teach the interface.

Proposed acceptance targets, to calibrate after the first baseline:

- At least 80% complete the first lesson without facilitator help.
- Median time to first meaningful training action is under three minutes.
- At least 80% can locate their saved line and next review without explanation.
- Returning users can start or resume the recommended session in two interactions or fewer.
- No known critical data-loss, incorrect-turn, illegal-move or duplicate-reward defects at release.
- Key screen content becomes usable within 2.5 seconds under the agreed representative mobile test profile; normal board actions show immediate acknowledgement and never block on an unrelated analysis job.

Measure first-session activation, first-session completion, return for a later review, weekly training participation, unhinted delayed recall and optional in-game adherence. Inspect abandonment by step and device. Establish real retention baselines before setting growth targets. XP earned and raw time spent are supporting signals, not proof of learning.

Test the behaviours that can break trust: both sides of the board; castling, en passant and promotion; transpositions; multi-variation PGN import/export; malformed imports; state migration; timezone changes and due dates; hints/reveals; session recovery; concurrent sync; missing engine/book data; empty queues; duplicate submissions; course-version changes; deletion undo.

Separate training correctness tests from UI journey tests. Add visual checks for the main phone/desktop layouts and all feedback states. Test the local and hosted API contracts for equivalent core behaviour. Every release needs reviewed chess content, working persistence and a credible way to recover a failed session.

## 12. Decisions and risks to resolve during the audit

| Decision or risk | Proposed default / response |
| --- | --- |
| What “full database” means | Opening explorer in core; complete searchable game archive as an explicit follow-on |
| Existing data volume and coverage | Inspect actual book and build metadata; do not rely on README counts alone |
| Lesson quality | Limit pilot scope and secure chess review before promising a large course library |
| Existing account sync | Verify deployed behaviour and migration paths before extending it |
| Repertoire learning versus engine grading | Recall grades the saved choice; sound alternatives receive distinct feedback |
| Too much UI | Four destinations; one active board panel; secondary tools disclosed in context |
| Excessive review backlog | Time-budgeted queues, new-learning limits and gentle catch-up |
| Sparse coverage estimates | Show scope and uncertainty; avoid a falsely precise headline percentage |
| Framework migration | Keep existing stack unless a time-boxed spike demonstrates clear value |
| Gamification eclipses chess | Tie rewards to eligible learning events and evaluate delayed recall separately |

## 13. Definition of the first successful release

A new player can explore an opening, save a repertoire, understand a short chapter, practise it, return for a scheduled review and see an honest account of progress. The app works comfortably on a phone. It has a clear next action, useful empty/error states, reliable persistence and no dependency on personal game import.

A returning player can identify an important unprepared reply, learn a response and see that gap close while recall remains independently measured. Game analysis can later confirm whether that preparation transfers into play.

The experience should feel complete with one repertoire before it grows into many.

## Source and evidence notes

- Repository: https://github.com/AdLgames/chess-opening-leak-analyzer
- Existing README: https://github.com/AdLgames/chess-opening-leak-analyzer/blob/main/README.md
- Current product requirements: https://github.com/AdLgames/chess-opening-leak-analyzer/blob/main/PHASE2_REQUIREMENTS.md
- Prior improvement plan: https://github.com/AdLgames/chess-opening-leak-analyzer/blob/main/IMPROVEMENT_PLAN.md
- Competitor context reviewed in the preceding discussion: https://www.chessreps.com/about

This document is a proposed build specification. Timelines, UX targets, XP values, pilot opening choices and session composition are planning assumptions to validate. No implementation or deployment is implied by this plan.
