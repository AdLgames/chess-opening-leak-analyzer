"""Generate a synthetic PGN archive so the analyzer can be demoed without private game data.

Each "line" is a repertoire fragment plus the score distribution the sample player gets with it.
"""
from __future__ import annotations

import io
import os
import random

import chess
import chess.pgn

PLAYER = "SamplePlayer"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_pgns")

# (label, eco, opening name, player color, SAN moves, (wins, draws, losses))
LINES = [
    ("sicilian_f3", "B50", "Sicilian Defense: Modern Variations",
     "white", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 f3 e5 Nb3 Be7 Bg5 O-O", (2, 1, 9)),
    ("italian_ng5", "C50", "Italian Game: Giuoco Pianissimo",
     "white", "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 Nxd5 Nxf7 Kxf7", (1, 0, 6)),
    ("qgd_exchange", "D35", "Queen's Gambit Declined: Exchange Variation",
     "white", "d4 d5 c4 e6 Nc3 Nf6 cxd5 exd5 Bg5 Be7 e3 O-O Bd3 c6", (7, 3, 2)),
    ("philidor_bg4", "C41", "Philidor Defense",
     "black", "e4 e5 Nf3 d6 d4 Bg4 dxe5 Bxf3 Qxf3 dxe5 Bc4 Qd7 Qb3", (1, 1, 8)),
    ("nimzo_main", "E32", "Nimzo-Indian Defense: Classical Variation",
     "black", "d4 Nf6 c4 e6 Nc3 Bb4 Qc2 O-O a3 Bxc3+ Qxc3 b6 Bg5 Bb7", (5, 4, 3)),
    ("caro_kann", "B12", "Caro-Kann Defense: Advance Variation",
     "black", "e4 c6 d4 d5 e5 Bf5 Nf3 e6 Be2 c5 Be3 Qb6 Nc3 Nc6", (4, 2, 4)),
    # Deliberate opening blunders so the engine pass has something to catch.
    ("italian_nxe5", "C50", "Italian Game: Giuoco Piano",
     "white", "e4 e5 Nf3 Nc6 Bc4 Bc5 Nxe5 Nxe5 d4 Bxd4 Nc3", (1, 0, 8)),
    ("qga_b5", "D20", "Queen's Gambit Accepted",
     "black", "d4 d5 c4 dxc4 e3 b5 a4 c6 axb5 cxb5 Qf3", (1, 1, 9)),
]

OPPONENTS = ["Opponent_A", "Opponent_B", "Opponent_C", "Opponent_D", "Opponent_E", "Opponent_F"]


def make_game(label: str, eco: str, name: str, color: str, sans: list[str], result: str,
              idx: int, rng: random.Random) -> chess.pgn.Game:
    game = chess.pgn.Game()
    opp = rng.choice(OPPONENTS)
    game.headers["Event"] = "Rated blitz game"
    game.headers["Site"] = f"https://lichess.org/{label}{idx:03d}"
    game.headers["Date"] = f"2026.0{rng.randint(1, 8)}.{rng.randint(10, 28)}"
    game.headers["White"] = PLAYER if color == "white" else opp
    game.headers["Black"] = opp if color == "white" else PLAYER
    game.headers["Result"] = result
    game.headers["ECO"] = eco
    game.headers["Opening"] = name
    game.headers["WhiteElo"] = str(rng.randint(1680, 1820))
    game.headers["BlackElo"] = str(rng.randint(1680, 1820))
    game.headers["TimeControl"] = "300+0"
    node = game
    board = chess.Board()
    for san in sans:
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)
    return game


def main() -> None:
    rng = random.Random(20260824)
    os.makedirs(OUT_DIR, exist_ok=True)
    buckets: dict[str, list[str]] = {"white_games.pgn": [], "black_games.pgn": []}
    for label, eco, name, color, moves, (win, draw, loss) in LINES:
        sans = moves.split()
        results: list[str] = []
        if color == "white":
            results += ["1-0"] * win + ["1/2-1/2"] * draw + ["0-1"] * loss
        else:
            results += ["0-1"] * win + ["1/2-1/2"] * draw + ["1-0"] * loss
        rng.shuffle(results)
        for i, result in enumerate(results, start=1):
            game = make_game(label, eco, name, color, sans, result, i, rng)
            out = io.StringIO()
            print(game, file=out, end="\n\n")
            buckets[f"{color}_games.pgn"].append(out.getvalue())
    for fname, games in buckets.items():
        path = os.path.join(OUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("".join(games))
        print(f"{path}: {len(games)} games")


if __name__ == "__main__":
    main()
