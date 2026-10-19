# Named opening routes

All five TSV volumes from https://github.com/lichess-org/chess-openings at the
commit recorded in source.json, retrieved 18 October 2026. The complete source
snapshot contains 3,865 rows and is dedicated to the public domain under CC0;
COPYING.txt is included. Checksums make builds reproducible without network.

These are named reference routes, not every possible chess continuation, a
ranking of move quality, or authored courses. The upstream description uses
well-known routes or common master-game move orders. Transpositions may appear
under several names. Our builder validates every move and merges forks by exact
position including side to move, castling and legal en-passant state.

Regenerate with `python chess_opening_analyzer/tools/build_opening_lines.py`.
The browser loads the index only on request, the selected ECO volume on demand,
and one of 64 position-fork shards as the board changes. Game frequencies remain
separate and come from the installed statistical book with its own scope.
