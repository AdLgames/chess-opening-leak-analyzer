"""Traceable position facts and imported decision evidence, never inferred thoughts."""

from __future__ import annotations
from collections import defaultdict
import math
from typing import Any
import chess
from .board import board_from, BoardError

PIECES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}
VALUE = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def finite(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def decision_context(fen: str, played: str, best: str = "") -> dict[str, Any]:
    board = board_from(fen)
    if not board.is_valid():
        raise BoardError(
            "The supplied position is not a valid standard chess position."
        )
    try:
        move = board.parse_san(played)
        if move not in board.legal_moves:
            raise ValueError("Not a legal move")
    except ValueError as exc:
        raise BoardError(
            "The played move is not legal in the supplied position."
        ) from exc
    colour = board.turn
    side = "White" if colour else "Black"
    facts = []
    tags = []
    if board.is_check():
        facts.append({"kind": "check", "text": f"{side} was in check before the move."})
        tags.append("in-check")
    after = board.copy()
    after.push(move)
    king = after.king(colour)
    if king in ([chess.E1, chess.D1] if colour else [chess.E8, chess.D8]):
        facts.append(
            {
                "kind": "king",
                "text": f"Your king is on {chess.square_name(king)} after {played}. This is position context, not proof that the move is bad.",
            }
        )
        tags.append("central-king")
    captures = []
    for reply in after.legal_moves:
        captured_square = reply.to_square
        if after.is_en_passant(reply):
            captured_square += -8 if after.turn == chess.WHITE else 8
        target = after.piece_at(captured_square)
        if not after.is_capture(reply) or not target or target.color != colour:
            continue
        next_board = after.copy()
        san = after.san(reply)
        next_board.push(reply)
        captures.append(
            {
                "uci": reply.uci(),
                "san": san,
                "piece": PIECES[target.piece_type],
                "square": chess.square_name(captured_square),
                "value": VALUE[target.piece_type],
                "fen": next_board.fen(),
                "from": chess.square_name(reply.from_square),
                "to": chess.square_name(reply.to_square),
            }
        )
    captures.sort(key=lambda c: (-c["value"], c["san"]))
    if captures:
        c = captures[0]
        facts.append(
            {
                "kind": "capture",
                "text": f'After {played}, {"Black" if colour else "White"} can legally play {c["san"]}, capturing your {c["piece"]} on {c["square"]}. Whether that capture is good requires further analysis.',
            }
        )
        tags.append("capture-available")
    alternative = None
    if best and best != played:
        try:
            choice = board.parse_san(best)
            if choice not in board.legal_moves:
                raise ValueError("Not a legal alternative")
            next_board = board.copy()
            next_board.push(choice)
            properties = []
            if board.is_castling(choice):
                properties.append("castles your king")
                tags.append("alternative-castles")
            if board.is_capture(choice):
                properties.append("makes a capture")
                tags.append("alternative-captures")
            if next_board.is_check():
                properties.append("gives check")
                tags.append("alternative-checks")
            alternative = {
                "uci": choice.uci(),
                "san": board.san(choice),
                "fen": next_board.fen(),
                "properties": properties,
            }
            facts.append(
                {
                    "kind": "alternative",
                    "text": f'The report’s first engine alternative is {alternative["san"]}'
                    + (", which " + " and ".join(properties) if properties else "")
                    + ". This is the report’s recommendation, not a new engine search.",
                }
            )
        except ValueError:
            pass
    return {
        "version": 1,
        "fen": board.fen(),
        "played": board.san(move),
        "playedUci": move.uci(),
        "after": after.fen(),
        "side": side.lower(),
        "facts": facts,
        "captures": captures[:3],
        "alternative": alternative,
        "tags": tags,
        "scope": "Legal board facts and the supplied report alternative; no psychological or causal diagnosis.",
    }


def build_decision_evidence(rows, games=()):
    by_position = defaultdict(dict)
    wanted = {
        " ".join(str(r.get("fen", "")).split()[:4]) + "|" + str(r.get("your_move", ""))
        for r in rows[:120]
    }
    for game in games:
        for rec in game.plies:
            key = " ".join(rec.fen_before.split()[:4]) + "|" + rec.san
            if key not in wanted:
                continue
            by_position[key].setdefault(
                (game.game_id, rec.ply),
                {
                    "game": game.game_id,
                    "date": game.date,
                    "ply": rec.ply,
                    "clockAfter": getattr(rec, "clock_after", None),
                    "spent": getattr(rec, "spent_seconds", None),
                    "spentSource": getattr(rec, "spent_source", ""),
                    "timeControl": getattr(rec, "time_control", ""),
                },
            )
    decisions = []
    for row in rows[:120]:
        try:
            context = decision_context(
                row["fen"], row["your_move"], row.get("engine_best_1", "")
            )
        except (BoardError, KeyError):
            continue
        key = " ".join(context["fen"].split()[:4]) + "|" + context["played"]
        sources = list(by_position.get(key, {}).values())
        clocks = [s for s in sources if s["clockAfter"] is not None]
        decisions.append(
            {
                "key": key,
                "context": context,
                "reportedOccurrences": max(0, int(finite(row.get("your_games")) or 0)),
                "uniqueSourceGames": len({s["game"] for s in sources}),
                "sourceDecisions": len(sources),
                "clockSamples": len(clocks),
                "under60Seconds": sum(s["clockAfter"] < 60 for s in clocks),
                "sources": sources[:8],
                "sourcesTruncated": len(sources) > 8,
            }
        )
    return {
        "version": 1,
        "decisions": decisions,
        "flaggedRows": len(rows),
        "includedRows": len(decisions),
        "scope": "Latest imported opening-phase report. Counts are not combined across repeated imports. Clock readings are included only when recorded in the PGN. Tags describe context, not causes.",
    }
