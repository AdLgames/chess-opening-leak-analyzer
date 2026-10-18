# Tactical starter pack v1

`puzzles-v1.json` is a fixed subset of the Lichess puzzle database, downloaded
18 October 2026 from <https://database.lichess.org/lichess_db_puzzle.csv.zst>.
Lichess releases the database under **CC0**:
<https://database.lichess.org/#puzzles>.
Source IDs, original FEN, solution, themes, rating snapshot and game URLs are
retained. No player account or private game data is used.

Selection: 25 distinct positions per theme (fork, pin, hangingPiece,
discoveredAttack, backRankMate, mateIn1), source rating 500–1550, popularity at
least 85, at least 1000 plays, and at most three learner moves. A motif tag is a
source classification, not an engine verdict or a complete difficulty measure.
The pack includes both colours; some positions come from later in a game.
It is a general tactics pack, not personalised opening coverage.

Run `python chess_opening_analyzer/tools/build_puzzles.py` to rebuild the six
small lazy-loaded packs and the catalog. The compiler applies the source's
**first move as the opponent's setup**, verifies all legal solution transitions,
and includes every legal mating alternative in mate-in-one positions. Normal
puzzle play uses these checked moves without live engine requests. Every
exercise links back to its Lichess source position.

Twelve original short teaching sequences introduce these motifs using two
examples per theme. The compiler derives move and attack diagrams from
python-chess. Geometric attacks are labelled separately from legal captures.
These are micro-lessons, not twelve additional opening courses. The existing
three opening courses and their saved IDs remain unchanged.
