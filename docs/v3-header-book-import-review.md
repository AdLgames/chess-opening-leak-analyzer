# V3.1 review additions — a chess corner with a purpose

The latest review feedback adds three connected improvements to PR #36.

## A header that belongs to this site

The workspace header and navigation now share the public site's forest, cream,
leaf green and lilac palette, original mark and illustrated guide. A small
checker detail and soft menu shapes replace the generic toolbar appearance.
The four destinations remain unchanged.

On phones and tablets, the navigation button opens a labelled drawer with
keyboard focus containment, Escape/outside close and focus restoration. Tools
holds game import, line building, help and the existing report exports/Run again
controls. Profile and account controls remain directly accessible. The header
stays 54px on small screens so the board keeps its space.

Public navigation uses the same identity, a useful menu on phones/tablets, and a
clear Bring my games action. Static links remain available without JavaScript.

## Book moves earn a little encouragement

When a player makes a move in the explorer, the guide reacts to that actual
move. A book reaction requires a matching UCI move with recorded games in the
**position before the move**. The reply reports the real sample count. Exact
course-position matches also reuse the authored explanation of the move.

Maya, Theo and Inez have original positive lines, such as “Your pieces have done
their homework” and “Somewhere, an opening manual just nodded.” The played move
can appear in the quip. A move outside the available book gets curious, neutral
feedback; absence from the database is not presented as a chess mistake.

Navigation, replay, undo and reset do not award book praise. Failed or stale
position requests cannot announce an unapplied move. Quiet/reduced-motion
preferences still apply, and exploration creates no recall result or reward.
Existing training continues to distinguish the prepared answer from other
legal choices; database popularity is not an engine verdict.

## Bring your games, deliberately

A substantial illustrated invitation appears below the working board, on the
homepage and on course pages. It connects the benefit—finding opening decisions
worth practising—to the next action. The app hides it during training/puzzles
and for players who already have imported-game evidence.

Provider buttons open the established analysis flow with Lichess or Chess.com
selected. The introduction shows Account → Choose games → Choose practice.
Signing in via Lichess or email retains that provider and any entered username,
including through the header's sign-in button. Lichess's linked username can be
prefilled on return. New connection links never start analysis automatically:
the player reviews the existing game/time-control settings and starts the run.
Returning players open those settings in the existing Run again dialog, keeping
the current report intact. Invitations cannot change an analysis in flight.
Legacy explicit “Find my patterns” links retain their signed-in behaviour;
signed-out visitors first receive the account handoff instead of a failed run.

**Chess.com is a public-username import, not Chess.com OAuth.** No chess-site
password is requested. Only configured sign-in methods are offered. Deployments
without accounts keep their existing local import capability and say that
progress stays on the device. No new email provider, remote account permission
or analytics collection is introduced.

## Verification and images

The pull request's CI runs the complete Python and browser release suites.
The additional browser checks cover all guide voices, both colours, exact book
provenance, failed moves, provider and username retention, email/OAuth redirect
payloads, linked-account prefilling, menus, dialogs, exports and CTA visibility.
Accessibility checks cover the new menus, banners and signup states in light
and dark themes and at phone, tablet and desktop widths.

| Experience | Desktop | Phone |
| --- | --- | --- |
| Header and book reaction | [1440px](review/v3-book-header-1440.png) | [390px](review/v3-book-header-390.png) |
| Workspace invitation | [1440px](review/v3-invitation-1440.png) | [390px](review/v3-invitation-390.png) |
| Provider/sign-in handoff | [1440px](review/v3-import-invite-1440.png) | [390px](review/v3-import-invite-390.png) |
| Homepage invitation | [1440px](review/v3-public-invitation-1440.png) | [390px](review/v3-public-invitation-390.png) |
| Menus | — | [Workspace](review/v3-navigation-390.png) · [Public](review/v3-public-menu-390.png) |

The sign-in screenshots use the test configuration with both supported methods
enabled; each deployment shows the methods actually available there.

## Useful next slices from the roadmap

1. **Provider and import status.** A clear record of the source, last successful
   import and game filters, with an explicit reimport action. Extend durable
   queued writes to repertoire edits and reports before promising seamless
   offline sync for all account data; V3.1 queues learning records today.
2. **A guided first finding.** After a real import, take one supported decision
   through What happened → Why → Try again → Save for review. Reuse the existing
   game exercises and handle small samples/no findings honestly. This is a
   smaller next slice than complete whole-game review or full bot games.
3. **Three more authored opening courses.** London, Alapin and French Advance
   are already proposed. Prioritise checked explanations and useful replies,
   with chess-content review, rather than relabelling database entries as courses.

Full bot matches still need the engine/mobile performance gate in V3.2. Social
features and installable offline packs remain later phases. These additions
finish the current review slice without changing that delivery order.
