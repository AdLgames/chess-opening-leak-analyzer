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
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

LICHESS_DB = "https://explorer.lichess.ovh/lichess"
MASTERS_DB = "https://explorer.lichess.ovh/masters"
USER_AGENT = "chess-opening-analyzer/1.0 (+https://github.com/)"


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
