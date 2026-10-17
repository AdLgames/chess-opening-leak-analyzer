# Board-centred chess workspace: review guide

17 October 2026 · Draft PR #30 · Interface milestone

The board is the main workspace. Today opens directly onto a large playable board
with a compact study panel, without an import, sign-in gate or introductory hero.
Explore is an opening library with real position previews and playable lines.
The four destinations, existing analysis tools and saved-data formats are retained.

## Review the experience

1. Open `/app/`. The study board is immediately visible and playable. Use taps,
   keyboard square navigation, or **Moves** → a book-reply button.
2. Choose **Walk through line**. Use the arrows to move forward and back through
   the opening. Try a different legal move; it creates a new continuation instead
   of silently retaining the old future moves. The actual move order is saved.
3. Open Explore. Browse 20 opening guides and their board previews. Filter by
   side or search by name, moves or ECO. Select a guide to open its starting
   position; its Study panel contains the plan and two further continuations.
4. Choose a continuation, inspect the replies in Moves and save a named line with
   a note. It appears in **Your lines** and Repertoire. Reload and reopen it.
5. Try a named database search result or enter a SAN line/FEN under Board tools.
   Position-based lines retain the FEN when exported as PGN.
6. Use Tools → Analyse games → sample archive. Existing report filters, charts,
   position review, drills, exports and return navigation remain available.
7. Repeat on a phone. The board and its controls appear before the study text;
   the four labelled bottom-navigation items remain available.

## Screenshots

| Study board, desktop | Opening library, desktop |
| --- | --- |
| ![Large playable board and compact study panel](review/today-desktop.png) | ![Opening library with real position previews](review/explore-desktop.png) |

| Study board, phone | Saved repertoire, phone |
| --- | --- |
| ![Board above controls and study text on a phone](review/explore-mobile.png) | ![Saved line and note with position preview](review/repertoire-mobile.png) |

## Opening content

The library contains 20 original study guides: Italian, Ruy Lopez, Scotch, Vienna,
London, Queen’s Gambit, English, Réti, Caro-Kann, Sicilian, Najdorf, Dragon, Kan,
French, Scandinavian, Pirc, Queen’s Gambit Declined, Slav, Nimzo-Indian and King’s
Indian. Each has a starting line, two named continuations, an explanation and a
plan. All 60 move sequences and the 20 catalogue previews are legally validated.

These are opening references, not accredited courses or graded lessons. No
instructor endorsements, fabricated course counts or made-up learning results
are displayed. Frequency/results continue to come from the real opening book;
additional named database positions remain available through search.

## Preservation and architecture

- One board instance stays alive across navigation. Existing Python legal-move
  and opening-book APIs remain the source of chess legality and statistics.
- Saved repertoire choices, drills, runs, report and preferences retain their
  `leaklab:` keys and account API shapes. The versioned baseline backup is retained.
- Names, notes, side, starting FEN and actual explored path survive save/reopen,
  account sync and revisiting the same choice in the existing prep editor.
- Save feedback confirms device persistence only. Storage failures keep a tab
  copy and display an accurate message; failed board requests retain the line.
- Explicit appearance preferences are respected; new visitors get the dark
  workspace. Fonts are served locally. SVG boards and keyboard semantics are shared.
- Legacy hashes, analysis, prep, engine tools, exports and authentication rules
  remain available. Analysis authentication never gates opening exploration.

## Validation

- **204 Python tests passed**, including real PostgreSQL state tests, the hosted
  bundle and legality checks for every advertised study line and board preview.
- **18 Chromium browser journeys passed**, including guest play, White/Black
  saved lines, notes, legal PGN/FEN exports, migration/backup, storage quota failure,
  request recovery, named database search, variation selection, line replay,
  forward/back branching, keyboard tabs, phone touch/promotion and existing analysis.
- Layouts checked at 360×800, 390×844, 768×1024 and 1440×1000. The playable board
  is visible on entry, with no horizontal document/main overflow.
- Axe WCAG 2 A/AA and 2.1 AA scans of all four destinations reported no violations
  at desktop and 360px widths. Automated scans do not replace human usability review.
- Hosted bundle assembly, JavaScript syntax checks and diff whitespace checks passed.

The milestone remains a reviewable interface and opening-study foundation. Formal
lesson grading, a review scheduler, preparedness scoring and rewards remain outside
this change. No production merge is included.
