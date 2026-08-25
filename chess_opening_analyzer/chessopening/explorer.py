"""Lichess Opening Explorer client: disk-cached, rate-limit aware, offline-safe.

API docs: https://lichess.org/api#tag/Opening-Explorer
Endpoints used:
  GET https://explorer.lichess.ovh/lichess   (public Lichess games, filter by rating/speed)
  GET https://explorer.lichess.ovh/masters   (OTB master games)
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

# Lichess asks that clients identify themselves and offer a way to reach a human. The
# value here used to be "+https://github.com/", a link to nothing, which is worse than
# sending no URL at all. One definition, shared with the archive fetcher.
from .ingest import USER_AGENT

LICHESS_DB = "https://explorer.lichess.ovh/lichess"
MASTERS_DB = "https://explorer.lichess.ovh/masters"

# One-sided 80% normal quantile, used to ask "is the player below the book even at the
# generous end of their own record?".
#
# Calibrated deliberately: at 90% a player scoring 11% over 9 games against a 23% baseline
# is not flagged, which throws away a real and useful finding. This is a coaching tool, so a
# missed leak costs as much as a spurious one — 80% keeps that case while still suppressing
# the three-game samples that motivated the check. Tunable per run via `analyze(confidence_z=)`.
Z_CONFIDENCE = 0.8416

# Games of the position's own average a book move is shrunk toward. A move with 2 games ends
# up almost entirely at the position mean; a move with 2000 keeps its own score.
BOOK_PRIOR_GAMES = 50


def score_interval(
    white: int, draws: int, black: int, color: str, z: float = Z_CONFIDENCE
) -> tuple[float, float, float] | None:
    """`(score, low, high)` for `color` from a win/draw/loss record.

    The per-game score takes three values (1, 0.5, 0), so the spread is the trinomial
    variance of that score rather than the binomial variance a plain win rate would use —
    a record full of draws is genuinely more certain than one that swings between wins and
    losses, and this reflects that.
    """
    n = white + draws + black
    if n <= 0:
        return None
    wins = white if color == "white" else black
    losses = black if color == "white" else white
    score = (wins + 0.5 * draws) / n
    variance = (
        wins * (1.0 - score) ** 2 + draws * (0.5 - score) ** 2 + losses * score**2
    ) / n
    # A record with one repeated result has zero sample variance, which would claim
    # certainty from very little evidence. Never let the standard error fall below the
    # effect of half a point spread over the games seen.
    stderr = max(math.sqrt(variance / n), 0.5 / n)
    return score, max(0.0, score - z * stderr), min(1.0, score + z * stderr)


def shrink_toward(score: float, games: int, prior_score: float, prior_games: int = BOOK_PRIOR_GAMES) -> float:
    """Pull a thinly-sampled score toward a prior, in proportion to how thin it is."""
    if games <= 0:
        return prior_score
    return (score * games + prior_score * prior_games) / (games + prior_games)


@dataclass
class MoveStats:
    uci: str
    san: str
    white: int
    draws: int
    black: int
    average_rating: int | None = None

    @property
    def games(self) -> int:
        return self.white + self.draws + self.black

    def score_for(self, color: str) -> float | None:
        """Expected score (0-1) for `color` after this move is played."""
        if self.games == 0:
            return None
        wins = self.white if color == "white" else self.black
        return (wins + 0.5 * self.draws) / self.games


@dataclass
class PositionStats:
    eco: str
    name: str
    white: int
    draws: int
    black: int
    moves: list[MoveStats]
    offline: bool = False

    @property
    def games(self) -> int:
        return self.white + self.draws + self.black

    def score_for(self, color: str) -> float | None:
        if self.games == 0:
            return None
        wins = self.white if color == "white" else self.black
        return (wins + 0.5 * self.draws) / self.games

    def move(self, uci: str) -> MoveStats | None:
        for m in self.moves:
            if m.uci == uci:
                return m
        return None

    def popularity(self, uci: str) -> float | None:
        """Share of database games in which this move was chosen."""
        total = sum(m.games for m in self.moves)
        m = self.move(uci)
        if not total or m is None:
            return None
        return m.games / total

    def baseline_for(
        self, uci: str, color: str, min_move_games: int = 30, prior_games: int = BOOK_PRIOR_GAMES
    ) -> tuple[float, str, int] | None:
        """The score to hold the player to for this move: `(score, source, games)`.

        A move needs `min_move_games` behind it before its own record is used at all, and
        even then it is shrunk toward the position average — two games in a 2013 dump must
        not be able to claim a confident 100%. Below the floor the position's own score is
        the honest comparison, and `source` records which was used so the interface can say.
        """
        position_score = self.score_for(color)
        if position_score is None:
            return None
        move = self.move(uci)
        if move is None or move.games < min_move_games:
            return position_score, "position", self.games
        move_score = move.score_for(color)
        if move_score is None:
            return position_score, "position", self.games
        return (
            shrink_toward(move_score, move.games, position_score, prior_games),
            "move",
            move.games,
        )

    def best_by_score(self, color: str, min_games: int = 50) -> list[MoveStats]:
        cands = [m for m in self.moves if m.games >= min_games]
        cands.sort(key=lambda m: (m.score_for(color) or 0.0), reverse=True)
        return cands


EMPTY = PositionStats(eco="", name="", white=0, draws=0, black=0, moves=[], offline=True)


class OpeningExplorer:
    def __init__(
        self,
        cache_dir: str,
        db: str = "lichess",
        speeds: str = "blitz,rapid,classical",
        ratings: str = "1600,1800,2000",
        offline: bool = False,
        min_interval: float = 1.2,
        timeout: float = 20.0,
        max_retries: int = 4,
    ):
        self.cache_dir = cache_dir
        self.db = db
        self.speeds = speeds
        self.ratings = ratings
        self.offline = offline
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_call = 0.0
        self.stats = {"cache_hits": 0, "api_calls": 0, "errors": 0}
        os.makedirs(cache_dir, exist_ok=True)

    # ---------------- internals ----------------
    def _params(self, play: str) -> dict[str, str]:
        if self.db == "masters":
            return {"play": play, "topGames": "0", "moves": "20"}
        return {
            "variant": "standard",
            "play": play,
            "speeds": self.speeds,
            "ratings": self.ratings,
            "topGames": "0",
            "recentGames": "0",
            "moves": "20",
        }

    def _cache_path(self, params: dict[str, str]) -> str:
        key = self.db + "|" + urllib.parse.urlencode(sorted(params.items()))
        return os.path.join(self.cache_dir, hashlib.sha1(key.encode()).hexdigest() + ".json")

    def _throttle(self) -> None:
        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

    def _get(self, params: dict[str, str]) -> dict | None:
        url = (MASTERS_DB if self.db == "masters" else LICHESS_DB) + "?" + urllib.parse.urlencode(params)
        for attempt in range(self.max_retries):
            self._throttle()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    self.stats["api_calls"] += 1
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 429:  # explorer asks for a full minute back-off
                    time.sleep(min(60, 5 * (attempt + 1) ** 2))
                    continue
                self.stats["errors"] += 1
                return None
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                time.sleep(1.5 * (attempt + 1))
        self.stats["errors"] += 1
        return None

    # ---------------- public ----------------
    def lookup(self, play_uci_csv: str) -> PositionStats:
        """Stats for the position reached by the comma-separated UCI move list."""
        params = self._params(play_uci_csv)
        path = self._cache_path(params)
        raw: dict | None = None
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    raw = json.load(fh)
                self.stats["cache_hits"] += 1
            except (OSError, json.JSONDecodeError):
                raw = None
        if raw is None:
            if self.offline:
                return EMPTY
            raw = self._get(params)
            if raw is None:
                return EMPTY
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(raw, fh)
            os.replace(tmp, path)
        return self.parse(raw)

    @staticmethod
    def parse(raw: dict) -> PositionStats:
        opening = raw.get("opening") or {}
        moves = [
            MoveStats(
                uci=m.get("uci", ""),
                san=m.get("san", ""),
                white=int(m.get("white", 0)),
                draws=int(m.get("draws", 0)),
                black=int(m.get("black", 0)),
                average_rating=m.get("averageRating"),
            )
            for m in raw.get("moves", [])
        ]
        return PositionStats(
            eco=opening.get("eco", "") or "",
            name=opening.get("name", "") or "",
            white=int(raw.get("white", 0)),
            draws=int(raw.get("draws", 0)),
            black=int(raw.get("black", 0)),
            moves=moves,
        )
