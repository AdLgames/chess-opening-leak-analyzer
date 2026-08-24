"""Load a folder of PGN files and turn them into opening-phase records."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterator

import chess
import chess.pgn

PGN_EXTS = (".pgn", ".PGN")


@dataclass
class PlyRecord:
    """One move played by the analysed player inside the opening phase."""

    game_id: str
    source_file: str
    white: str
    black: str
    result: str            # "1-0" / "0-1" / "1/2-1/2" / "*"
    player_color: str      # "white" | "black"
    player_score: float    # 1.0 win, 0.5 draw, 0.0 loss (from player POV)
    eco: str
    opening: str
    date: str
    ply: int               # 1-based ply index in the game
    move_number: int
    fen_before: str        # full FEN of position before the move
    epd_before: str        # FEN without clocks -> position key
    uci: str
    san: str
    line_san: str          # SAN moves up to and including this move, space separated
    line_uci: str          # comma separated UCI history (Lichess explorer `play` param)


@dataclass
class GameSummary:
    game_id: str
    source_file: str
    white: str
    black: str
    result: str
    player_color: str
    player_score: float
    eco: str
    opening: str
    date: str
    plies: list[PlyRecord] = field(default_factory=list)


_RESULT_SCORE = {"1-0": (1.0, 0.0), "0-1": (0.0, 1.0), "1/2-1/2": (0.5, 0.5)}


def find_pgn_files(folder: str) -> list[str]:
    if os.path.isfile(folder):
        return [folder]
    out: list[str] = []
    for root, _dirs, files in os.walk(folder):
        for f in sorted(files):
            if f.endswith(PGN_EXTS):
                out.append(os.path.join(root, f))
    return out


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def detect_main_player(files: list[str], sample_games: int = 400) -> str | None:
    """Guess whose games these are: the name appearing most often as White or Black."""
    counts: dict[str, int] = {}
    seen = 0
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            while seen < sample_games:
                headers = chess.pgn.read_headers(fh)
                if headers is None:
                    break
                seen += 1
                for tag in ("White", "Black"):
                    n = headers.get(tag, "")
                    if n and n != "?":
                        counts[n] = counts.get(n, 0) + 1
        if seen >= sample_games:
            break
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def load_games(
    folder: str,
    player: str,
    max_moves: int = 15,
    color: str = "both",
    min_result_known: bool = True,
) -> Iterator[GameSummary]:
    """Yield one GameSummary per game where `player` participated.

    max_moves is counted in full moves, so 15 -> the first 30 plies.
    """
    target = _norm(player)
    max_ply = max_moves * 2
    for path in find_pgn_files(folder):
        base = os.path.basename(path)
        with open(path, encoding="utf-8", errors="replace") as fh:
            idx = 0
            while True:
                game = chess.pgn.read_game(fh)
                if game is None:
                    break
                idx += 1
                h = game.headers
                white, black = h.get("White", "?"), h.get("Black", "?")
                if _norm(white) == target:
                    player_color = "white"
                elif _norm(black) == target:
                    player_color = "black"
                else:
                    continue
                if color != "both" and color != player_color:
                    continue
                result = h.get("Result", "*")
                if result not in _RESULT_SCORE:
                    if min_result_known:
                        continue
                    scores = (0.5, 0.5)
                else:
                    scores = _RESULT_SCORE[result]
                player_score = scores[0] if player_color == "white" else scores[1]

                gid = f"{base}#{idx}"
                summary = GameSummary(
                    game_id=h.get("Site", gid) if h.get("Site", "?") != "?" else gid,
                    source_file=base,
                    white=white,
                    black=black,
                    result=result,
                    player_color=player_color,
                    player_score=player_score,
                    eco=h.get("ECO", ""),
                    opening=h.get("Opening", "") or h.get("Variation", ""),
                    date=h.get("UTCDate", "") or h.get("Date", ""),
                )

                board = game.board()
                history_uci: list[str] = []
                history_san: list[str] = []
                for ply, move in enumerate(game.mainline_moves(), start=1):
                    if ply > max_ply:
                        break
                    san = board.san(move)
                    mover_is_player = (board.turn == chess.WHITE) == (player_color == "white")
                    if mover_is_player:
                        summary.plies.append(
                            PlyRecord(
                                game_id=summary.game_id,
                                source_file=base,
                                white=white,
                                black=black,
                                result=result,
                                player_color=player_color,
                                player_score=player_score,
                                eco=summary.eco,
                                opening=summary.opening,
                                date=summary.date,
                                ply=ply,
                                move_number=board.fullmove_number,
                                fen_before=board.fen(),
                                epd_before=board.epd(),
                                uci=move.uci(),
                                san=san,
                                line_san=" ".join(history_san + [san]),
                                line_uci=",".join(history_uci + [move.uci()]),
                            )
                        )
                    history_uci.append(move.uci())
                    history_san.append(san)
                    board.push(move)
                yield summary
