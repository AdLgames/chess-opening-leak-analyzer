"""Stockfish (UCI) analysis of opening positions: eval drops and better alternatives."""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, asdict

import chess
import chess.engine

MATE_CP = 10000

#: engine binaries bundled with the package (see tools/install_stockfish.py)
BUNDLED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")


def bundled_engine() -> str | None:
    for name in ("stockfish", "stockfish.exe"):
        p = os.path.join(BUNDLED_DIR, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def find_engine(explicit: str | None = None) -> str:
    """Locate Stockfish: explicit path, bundled copy, $STOCKFISH_PATH, then $PATH."""
    for cand in (explicit, bundled_engine(), os.environ.get("STOCKFISH_PATH"),
                 "stockfish", "stockfish.exe", "/usr/games/stockfish"):
        if not cand:
            continue
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    raise FileNotFoundError(
        "Stockfish not found. Bundle a local copy with `python tools/install_stockfish.py`, "
        "or install it system-wide (apt install stockfish / brew install stockfish), "
        "or pass --engine /path/to/stockfish, or set STOCKFISH_PATH."
    )


def _cp(score: chess.engine.PovScore, color: chess.Color) -> int:
    """Centipawns from `color`'s point of view, mates clamped."""
    return score.pov(color).score(mate_score=MATE_CP)


@dataclass
class Alternative:
    san: str
    uci: str
    cp: int


@dataclass
class PositionEval:
    """Engine verdict on one move played from `fen`."""

    fen: str
    played_uci: str
    played_san: str
    mover: str                 # "white" | "black"
    best_cp: int               # eval of the position for the mover if they play the best move
    played_cp: int             # eval for the mover after the move actually played
    eval_drop_cp: int          # best_cp - played_cp (>= 0)
    played_rank: int | None    # rank of the played move in the engine's MultiPV list
    alternatives: list[Alternative]
    depth: int

    @property
    def eval_drop_pawns(self) -> float:
        return round(self.eval_drop_cp / 100.0, 2)


class EngineAnalyzer:
    def __init__(
        self,
        engine_path: str | None = None,
        depth: int = 18,
        movetime_ms: int | None = None,
        multipv: int = 3,
        threads: int = 2,
        hash_mb: int = 256,
        cache_path: str | None = None,
    ):
        self.engine_path = find_engine(engine_path)
        self.depth = depth
        self.movetime_ms = movetime_ms
        self.multipv = max(1, multipv)
        self.threads = threads
        self.hash_mb = hash_mb
        self.cache_path = cache_path
        self._cache: dict[str, dict] = {}
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, encoding="utf-8") as fh:
                    self._cache = json.load(fh)
            except (OSError, json.JSONDecodeError):
                self._cache = {}
        self._engine: chess.engine.SimpleEngine | None = None

    # ---------------- lifecycle ----------------
    def __enter__(self) -> "EngineAnalyzer":
        self._engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        try:
            self._engine.configure({"Threads": self.threads, "Hash": self.hash_mb})
        except chess.engine.EngineError:
            pass
        return self

    def __exit__(self, *exc) -> None:
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
        self.flush()

    def flush(self) -> None:
        if not self.cache_path:
            return
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        tmp = self.cache_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._cache, fh)
        os.replace(tmp, self.cache_path)

    # ---------------- analysis ----------------
    def _limit(self) -> chess.engine.Limit:
        if self.movetime_ms:
            return chess.engine.Limit(time=self.movetime_ms / 1000.0)
        return chess.engine.Limit(depth=self.depth)

    def evaluate_move(self, fen: str, played_uci: str) -> PositionEval:
        """Compare the move actually played against the engine's top choices."""
        key = f"{fen}|{played_uci}|d{self.depth}|t{self.movetime_ms}|pv{self.multipv}"
        if key in self._cache:
            data = dict(self._cache[key])
            data["alternatives"] = [Alternative(**a) for a in data["alternatives"]]
            return PositionEval(**data)

        if self._engine is None:
            raise RuntimeError("EngineAnalyzer must be used as a context manager")

        board = chess.Board(fen)
        mover = board.turn
        move = chess.Move.from_uci(played_uci)
        played_san = board.san(move) if move in board.legal_moves else played_uci

        infos = self._engine.analyse(board, self._limit(), multipv=self.multipv)
        if isinstance(infos, dict):
            infos = [infos]
        alts: list[Alternative] = []
        for info in infos:
            pv = info.get("pv") or []
            if not pv:
                continue
            alts.append(
                Alternative(san=board.san(pv[0]), uci=pv[0].uci(), cp=_cp(info["score"], mover))
            )
        best_cp = alts[0].cp if alts else 0
        played_rank = next((i + 1 for i, a in enumerate(alts) if a.uci == played_uci), None)

        if played_rank == 1:
            played_cp = best_cp
        else:
            board.push(move)
            info = self._engine.analyse(board, self._limit())
            played_cp = _cp(info["score"], mover)
            board.pop()

        result = PositionEval(
            fen=fen,
            played_uci=played_uci,
            played_san=played_san,
            mover="white" if mover == chess.WHITE else "black",
            best_cp=best_cp,
            played_cp=played_cp,
            eval_drop_cp=max(0, best_cp - played_cp),
            played_rank=played_rank,
            alternatives=alts,
            depth=self.depth,
        )
        self._cache[key] = asdict(result)
        return result
