"""What the player intends to play, and what they are not ready for.

The leak report can only talk about moves the player actually made, which leaves its
biggest blind spot exactly where a club player's anxiety lives: the reply they have never
seen. This module closes that gap in two steps.

First it infers a repertoire — at every position the player reached, the move they choose
most often is taken as what they mean to play. Nobody has to build a tree by hand; their
own games already describe one.

Then it walks that tree from the starting position. At the player's turn it follows their
intended move; at the opponent's turn it fans out over the book's replies, multiplying
probabilities down each branch. A branch the player has rarely or never faced, but which a
real opponent reaches often, is a gap worth preparing — and because the walk knows how
likely each branch is, the gaps come out ranked by how soon one will cost a game.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import chess


@dataclass
class Intent:
    """The move the player means to play in one position, read from their own games."""

    uci: str
    san: str
    games: int
    share: float  # of the player's games from this position, how many chose this move


def faced_counts(nodes: dict[Any, Any]) -> dict[str, int]:
    """How many games took the player into each position, keyed by EPD.

    A node records the position *before* one of the player's moves, so its key is exactly
    a position the player has had to find a move in — which is what "have I faced this?"
    means.
    """
    counts: dict[str, int] = defaultdict(int)
    for node in nodes.values():
        counts[node.epd] += node.n
    return dict(counts)


def build_repertoire(nodes: dict[Any, Any], color: str, min_games: int = 2) -> dict[str, Intent]:
    """The player's habitual move in each position they reached as `color`.

    Plurality wins: the move they play most often from a position is what they intend,
    even when they are inconsistent. `share` records how inconsistent, so the caller can
    tell a settled choice from a coin flip.
    """
    by_epd: dict[str, list[Any]] = defaultdict(list)
    for node in nodes.values():
        if node.player_color == color:
            by_epd[node.epd].append(node)

    repertoire: dict[str, Intent] = {}
    for epd, group in by_epd.items():
        total = sum(n.n for n in group)
        best = max(group, key=lambda n: n.n)
        if best.n >= min_games:
            repertoire[epd] = Intent(
                uci=best.played_uci,
                san=best.played_san,
                games=best.n,
                share=best.n / total if total else 0.0,
            )
    return repertoire


def _describe(line: list[str], first_turn: chess.Color) -> str:
    """A SAN line with real move numbers, e.g. `1.e4 c6 2.d4 d5`."""
    out: list[str] = []
    number = 1
    turn = first_turn
    for i, san in enumerate(line):
        if turn == chess.WHITE:
            out.append(f"{number}.{san}")
        else:
            out.append(f"{number}...{san}" if i == 0 else san)
            number += 1
        turn = not turn
    return " ".join(out)


def find_gaps(
    db,
    nodes: dict[Any, Any],
    color: str,
    max_plies: int = 12,
    min_reach: float = 0.02,
    min_faced: int = 3,
    top_replies: int = 6,
    min_book_games: int = 50,
) -> list[dict[str, Any]]:
    """Replies the player should expect but has barely met, ranked by how often they come up.

    `min_reach` prunes branches that fewer than that share of games ever reach — without it
    the walk explores rare sidelines for ever and reports things nobody will play. Everything
    reported is therefore both *likely* and *unfamiliar*, which is the pair that makes a gap
    worth preparing.
    """
    repertoire = build_repertoire(nodes, color)
    if not repertoire:
        return []
    faced = faced_counts(nodes)
    our_side = chess.WHITE if color == "white" else chess.BLACK

    gaps: list[dict[str, Any]] = []
    # board, probability of reaching it, the line so far, the last named opening
    stack: list[tuple[chess.Board, float, list[str], str, str]] = [
        (chess.Board(), 1.0, [], "", "")
    ]

    while stack:
        board, prob, line, eco, name = stack.pop()
        if len(line) >= max_plies or prob < min_reach:
            continue
        epd = board.epd()
        named = db.opening_name(epd)
        if named:
            eco, name = named

        if board.turn == our_side:
            intent = repertoire.get(epd)
            if intent is None:
                continue  # never been here; the branch above already reported it
            child = board.copy()
            try:
                child.push_uci(intent.uci)
            except (ValueError, AssertionError):
                continue
            stack.append((child, prob, [*line, intent.san], eco, name))
            continue

        # Opponent to move: fan out over what the book actually plays here.
        stats = db.lookup_epd(epd)
        total = sum(m.games for m in stats.moves)
        if total < min_book_games:
            continue
        for move in stats.moves[:top_replies]:
            share = move.games / total
            reach = prob * share
            if reach < min_reach:
                continue
            child = board.copy()
            try:
                child.push_uci(move.uci)
            except (ValueError, AssertionError):
                continue
            seen = faced.get(child.epd(), 0)
            if seen < min_faced:
                gaps.append({
                    "line": _describe([*line, move.san], chess.WHITE),
                    "reply": move.san,
                    "reply_uci": move.uci,
                    "eco": eco,
                    "opening": name,
                    "share_pct": round(100 * share, 1),
                    "reach_pct": round(100 * reach, 1),
                    "times_faced": seen,
                    "book_games": move.games,
                    "player_color": color,
                    "fen": child.fen(),
                    "explanation": _explain(move.san, line, share, seen, name),
                })
            if seen:
                stack.append((child, reach, [*line, move.san], eco, name))

    gaps.sort(key=lambda g: (-g["reach_pct"], g["times_faced"]))
    return gaps


def _explain(reply: str, line: list[str], share: float, seen: int, name: str) -> str:
    """One sentence a club player can act on."""
    where = f"in the {name}" if name else "here"
    after = f"after {_describe(line, chess.WHITE)}" if line else "from the start"
    met = (
        "you have never faced it"
        if seen == 0
        else f"you have faced it {'once' if seen == 1 else f'{seen} times'}"
    )
    return (
        f"{reply} {where} is played in {round(100 * share)}% of games {after}, and {met}. "
        "Work out what you would answer before it happens in a real game."
    )


COVERAGE_FIELDS = [
    "reach_pct", "share_pct", "times_faced", "player_color", "eco", "opening",
    "line", "reply", "book_games", "fen", "explanation",
]
