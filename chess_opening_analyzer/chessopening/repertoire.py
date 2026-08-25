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


def _bare_line(line: str) -> list[str]:
    """`1.e4 c6 2.Nc3` as `["e4", "c6", "Nc3"]` — move numbers stripped."""
    out = []
    for token in line.split():
        cleaned = token.split(".")[-1].lstrip(".")
        if cleaned:
            out.append(cleaned)
    return out


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
                    # A gap is its own kind of problem: nothing has gone wrong yet, and the
                    # response is preparation rather than correction.
                    "category": "knowledge",
                    "category_label": "Unfamiliar",
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
    "reach_pct", "share_pct", "times_faced", "player_color", "category", "eco", "opening",
    "line", "reply", "book_games", "fen", "explanation",
]


# ---------------------------------------------------------------- the tree

def _status(node: Any, is_leak: bool, mark_decision: str, score: float | None) -> str:
    """How a line in the tree should read at a glance.

    Order matters: a committed choice is what the player has decided, and saying "weak"
    over the top of that is the arguing-back behaviour the marks exist to stop. A flagged
    move outranks a good score, because the flag already accounts for the score.
    """
    if mark_decision == "committed":
        return "committed"
    if is_leak:
        return "weak"
    if score is not None and node.n >= 5 and score >= 0.55:
        return "strong"
    return "played"


def build_tree(
    nodes: dict[Any, Any],
    color: str,
    min_games: int = 2,
    max_plies: int = 12,
    leak_keys: set[tuple[str, str]] | None = None,
    marks: dict[tuple[str, str], Any] | None = None,
    gaps: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """The player's repertoire as a tree, drawn from the lines they actually played.

    Every decision already carries the move list that reached it, so the tree is the trie
    of those lines — no re-derivation, and opponent moves appear as the edges between the
    player's own. Each of the player's edges carries its record and how it is doing, so
    strong lines, weak lines and holes are one colour apart.
    """
    leak_keys = leak_keys or set()
    marks = marks or {}
    # A gap's line is the player's line plus the opponent reply they have not met, and it
    # is written with move numbers while a node's is not — so both are reduced to bare SAN
    # and the reply is dropped before matching.
    gaps_by_line: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for gap in gaps or []:
        if gap.get("player_color") != color:
            continue
        tokens = _bare_line(gap.get("line", ""))
        if tokens:
            gaps_by_line[" ".join(tokens[:-1])].append(gap)

    root: dict[str, Any] = {"children": {}}
    for node in nodes.values():
        if node.player_color != color or node.n < min_games:
            continue
        ucis = [u for u in node.line_uci.split(",") if u][:max_plies]
        if not ucis:
            continue

        board = chess.Board()
        cursor = root
        for depth, uci in enumerate(ucis, start=1):
            try:
                move = chess.Move.from_uci(uci)
                san = board.san(move)
            except (ValueError, AssertionError):
                break
            child = cursor["children"].get(uci)
            if child is None:
                child = cursor["children"][uci] = {
                    "uci": uci, "san": san, "ply": depth, "children": {},
                    "ours": False, "games": 0, "score_pct": None, "status": "played",
                    "opening": "", "epd": board.epd(), "fen": board.fen(), "gaps": 0,
                }
            board.push(move)
            # The last move of this line is the player's own decision, and the only edge
            # we have a record for.
            if depth == len(ucis):
                mark = marks.get((child["epd"], color))
                decision = mark.decision if mark and mark.uci == uci else ""
                child.update({
                    "ours": True,
                    "games": node.n,
                    "score_pct": round(100 * node.score, 1),
                    "opening": node.opening or node.eco or "",
                    "status": _status(node, (node.epd, uci) in leak_keys, decision, node.score),
                    "line": node.line_san,
                    "gaps": len(gaps_by_line.get(node.line_san, [])),
                })
            cursor = child

    def to_list(branch: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        for child in branch["children"].values():
            item = {k: v for k, v in child.items() if k != "children"}
            item["children"] = to_list(child)
            # A branching edge inherits the weight of everything below it, so the trunk
            # reads as the trunk rather than as whatever leaf happens to be biggest.
            if not item["ours"]:
                item["games"] = sum(c["games"] for c in item["children"]) or item["games"]
            out.append(item)
        out.sort(key=lambda c: (-c["games"], c["san"]))
        return out

    return to_list(root)


def tree_totals(tree: list[dict[str, Any]]) -> dict[str, int]:
    """How much of the repertoire is in each state, for a one-line summary."""
    counts = {"strong": 0, "weak": 0, "committed": 0, "played": 0, "gaps": 0}
    def walk(branch: list[dict[str, Any]]) -> None:
        for item in branch:
            if item.get("ours"):
                counts[item.get("status", "played")] = counts.get(item.get("status", "played"), 0) + 1
                counts["gaps"] += item.get("gaps", 0)
            walk(item.get("children", []))
    walk(tree)
    return counts
