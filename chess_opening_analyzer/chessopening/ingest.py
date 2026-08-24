"""Fetch a player's games straight from Lichess or Chess.com.

The rest of the pipeline reads PGN files from a folder, so ingestion's job is to end
up with exactly that: one PGN file per provider month under a cache directory, which
means a second run over the same window costs no requests at all.

    from chessopening.ingest import FetchOptions, fetch_games
    res = fetch_games(FetchOptions(provider="chesscom", username="hikaru", max_games=200))
    analyze(pgn_dir=res.pgn_dir, player=res.username, ...)

Only the standard library is used, and every request is sequential — both providers
ask for that, and Chess.com additionally wants a descriptive User-Agent.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Iterable

USER_AGENT = os.environ.get(
    "LEAKLAB_USER_AGENT",
    "OpeningLeakLab/0.2 (+https://github.com/AdLgames/chess-opening-leak-analyzer)",
)
DEFAULT_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "leaklab", "archives")
PROVIDERS = ("lichess", "chesscom")

# Chess.com calls them time classes, Lichess calls them perf types. One vocabulary in,
# provider spelling out.
SPEEDS = ("bullet", "blitz", "rapid", "classical", "daily")
_LICHESS_PERF = {
    "bullet": "bullet",
    "blitz": "blitz",
    "rapid": "rapid",
    "classical": "classical",
    "daily": "correspondence",
}

Progress = Callable[[str], None]


class IngestError(RuntimeError):
    """A fetch failed in a way the user can act on.

    `hint` carries the suggested next step and `download_url` a manual export page,
    so the dashboard can show something better than a status code.
    """

    def __init__(self, message: str, *, hint: str = "", download_url: str = "") -> None:
        super().__init__(message)
        self.hint = hint
        self.download_url = download_url


@dataclass
class FetchOptions:
    provider: str
    username: str
    max_games: int = 200
    speeds: tuple[str, ...] = ("blitz", "rapid", "classical")
    rated_only: bool = True
    since: str | None = None          # inclusive YYYY-MM-DD
    until: str | None = None          # inclusive YYYY-MM-DD
    token: str | None = None          # Lichess personal API token, optional
    cache_dir: str = DEFAULT_CACHE
    refresh: bool = False             # ignore cached months
    timeout: float = 30.0

    def normalised(self) -> "FetchOptions":
        provider = (self.provider or "").strip().lower()
        if provider in ("chess.com", "chess-com", "chesscom"):
            provider = "chesscom"
        if provider not in PROVIDERS:
            raise IngestError(
                f"Unknown provider {self.provider!r}.",
                hint=f"Use one of: {', '.join(PROVIDERS)}.",
            )
        username = (self.username or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.\-]{2,40}", username):
            raise IngestError(
                f"{username or 'That'} does not look like a username.",
                hint="Letters, digits, underscore, hyphen and dot only.",
            )
        speeds = tuple(s for s in (self.speeds or ()) if s in SPEEDS) or SPEEDS
        return FetchOptions(
            provider=provider,
            username=username,
            max_games=max(1, int(self.max_games)),
            speeds=speeds,
            rated_only=bool(self.rated_only),
            since=self.since or None,
            until=self.until or None,
            token=(self.token or None),
            cache_dir=self.cache_dir or DEFAULT_CACHE,
            refresh=bool(self.refresh),
            timeout=float(self.timeout),
        )


@dataclass
class FetchResult:
    provider: str
    username: str
    pgn_dir: str
    files: list[str] = field(default_factory=list)
    games: int = 0
    requests: int = 0
    cached_months: int = 0
    months: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "username": self.username,
            "pgn_dir": self.pgn_dir,
            "files": self.files,
            "games": self.games,
            "requests": self.requests,
            "cached_months": self.cached_months,
            "months": self.months,
            "notes": self.notes,
        }


# ------------------------------------------------------------------ http plumbing

def _get(url: str, *, timeout: float, accept: str, token: str | None = None,
         retries: int = 3) -> bytes:
    """GET with a descriptive agent, honouring 429/Retry-After with a backoff."""
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    delay = 2.0
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:
                wait = float(exc.headers.get("Retry-After") or delay)
                time.sleep(min(wait, 60.0))
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt == retries - 1:
                break
            time.sleep(delay)
            delay *= 2
    raise IngestError(
        f"Could not reach {urllib.parse.urlsplit(url).netloc}: {last}",
        hint="Check the connection, or upload a PGN export instead.",
    )


def _date_bounds(opts: FetchOptions) -> tuple[_dt.date | None, _dt.date | None]:
    def parse(value: str | None) -> _dt.date | None:
        if not value:
            return None
        try:
            return _dt.date.fromisoformat(value)
        except ValueError as exc:
            raise IngestError(f"Bad date {value!r}.", hint="Use YYYY-MM-DD.") from exc

    since, until = parse(opts.since), parse(opts.until)
    if since and until and since > until:
        raise IngestError("The start date is after the end date.")
    return since, until


def _cache_path(opts: FetchOptions, name: str) -> str:
    folder = os.path.join(opts.cache_dir, opts.provider, opts.username.lower())
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, name)


def _count_games(pgn_text: str) -> int:
    return len(re.findall(r"(?m)^\[Event ", pgn_text))


def _trim_to(pgn_text: str, limit: int) -> tuple[str, int]:
    """Keep at most `limit` games, cutting on game boundaries."""
    if limit <= 0:
        return "", 0
    parts = re.split(r"(?m)(?=^\[Event )", pgn_text)
    games = [p for p in parts if p.strip()]
    kept = games[:limit]
    return "\n\n".join(g.strip() for g in kept) + "\n", len(kept)


# ----------------------------------------------------------------- chess.com side

def _chesscom_months(opts: FetchOptions, progress: Progress) -> tuple[list[str], int]:
    url = f"https://api.chess.com/pub/player/{urllib.parse.quote(opts.username)}/games/archives"
    try:
        raw = _get(url, timeout=opts.timeout, accept="application/json")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise IngestError(
                f"Chess.com has no player called {opts.username}.",
                hint="Check the spelling — Chess.com usernames are not case sensitive.",
            ) from exc
        raise IngestError(f"Chess.com returned HTTP {exc.code} for the archive list.") from exc
    try:
        archives = json.loads(raw).get("archives") or []
    except json.JSONDecodeError as exc:
        raise IngestError("Chess.com sent an archive list that could not be read.") from exc
    if not archives:
        raise IngestError(f"{opts.username} has no games on Chess.com yet.")
    progress(f"chess.com: {len(archives)} monthly archives")
    return list(archives), 1


def _chesscom_keep(game: dict, opts: FetchOptions,
                   since: _dt.date | None, until: _dt.date | None) -> bool:
    if game.get("rules") != "chess" or not game.get("pgn"):
        return False
    if opts.rated_only and not game.get("rated", False):
        return False
    if game.get("time_class") not in opts.speeds:
        return False
    end = game.get("end_time")
    if (since or until) and end:
        day = _dt.datetime.fromtimestamp(int(end), _dt.timezone.utc).date()
        if since and day < since:
            return False
        if until and day > until:
            return False
    return True


def _fetch_chesscom(opts: FetchOptions, progress: Progress) -> FetchResult:
    since, until = _date_bounds(opts)
    archives, requests = _chesscom_months(opts, progress)
    result = FetchResult(provider="chesscom", username=opts.username,
                         pgn_dir=_cache_path(opts, ""), requests=requests)
    this_month = _dt.date.today().strftime("%Y/%m")
    remaining = opts.max_games

    for url in reversed(archives):                     # newest month first
        if remaining <= 0:
            break
        ym = "/".join(url.rstrip("/").split("/")[-2:])  # "2026/07"
        if since and ym < since.strftime("%Y/%m"):
            break
        if until and ym > until.strftime("%Y/%m"):
            continue
        path = _cache_path(opts, f"{ym.replace('/', '-')}.pgn")
        fresh_needed = opts.refresh or ym == this_month or not os.path.isfile(path)
        if not fresh_needed:
            text = open(path, encoding="utf-8").read()
            result.cached_months += 1
        else:
            try:
                raw = _get(url, timeout=opts.timeout, accept="application/json")
            except urllib.error.HTTPError as exc:
                progress(f"  {ym}: skipped (HTTP {exc.code})")
                result.notes.append(f"{ym} could not be fetched (HTTP {exc.code}).")
                continue
            result.requests += 1
            games = json.loads(raw).get("games") or []
            kept = [g["pgn"].strip() for g in games if _chesscom_keep(g, opts, since, until)]
            text = ("\n\n".join(kept) + "\n") if kept else ""
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        count = _count_games(text)
        if not count:
            continue
        if count > remaining:
            text, count = _trim_to(text, remaining)
            trimmed = _cache_path(opts, f"{ym.replace('/', '-')}.partial.pgn")
            with open(trimmed, "w", encoding="utf-8") as fh:
                fh.write(text)
            path = trimmed
        remaining -= count
        result.games += count
        result.files.append(path)
        result.months.append(ym)
        progress(f"  {ym}: {count} games ({result.games}/{opts.max_games})")

    if not result.games:
        raise IngestError(
            f"No games matched for {opts.username} on Chess.com.",
            hint="Widen the date range or the time controls, or turn off rated-only.",
        )
    return result


# ------------------------------------------------------------------ lichess side

def _fetch_lichess(opts: FetchOptions, progress: Progress) -> FetchResult:
    since, until = _date_bounds(opts)
    params: dict[str, str] = {
        "max": str(opts.max_games),
        "perfType": ",".join(sorted({_LICHESS_PERF[s] for s in opts.speeds})),
        "clocks": "false",
        "evals": "false",
        "opening": "true",
        "sort": "dateDesc",
    }
    if opts.rated_only:
        params["rated"] = "true"
    if since:
        params["since"] = str(int(_dt.datetime.combine(
            since, _dt.time.min, _dt.timezone.utc).timestamp() * 1000))
    if until:
        params["until"] = str(int(_dt.datetime.combine(
            until, _dt.time.max, _dt.timezone.utc).timestamp() * 1000))
    url = (f"https://lichess.org/api/games/user/{urllib.parse.quote(opts.username)}"
           f"?{urllib.parse.urlencode(params)}")
    download_url = f"https://lichess.org/@/{opts.username}/download"

    stamp = _dt.date.today().isoformat()
    path = _cache_path(opts, f"lichess-{stamp}-{opts.max_games}.pgn")
    result = FetchResult(provider="lichess", username=opts.username,
                         pgn_dir=_cache_path(opts, ""))
    if os.path.isfile(path) and not opts.refresh:
        text = open(path, encoding="utf-8").read()
        result.cached_months += 1
        progress("lichess: reusing today's cached export")
    else:
        progress(f"lichess: requesting up to {opts.max_games} games")
        try:
            raw = _get(url, timeout=opts.timeout, accept="application/x-chess-pgn",
                       token=opts.token)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise IngestError(
                    "Lichess refused the export without an API token.",
                    hint="Create a personal access token at lichess.org/account/oauth/token "
                         "and paste it in, or download your games and upload the file.",
                    download_url=download_url,
                ) from exc
            if exc.code == 404:
                raise IngestError(
                    f"Lichess returned no export for {opts.username}.",
                    hint="Check the username. If it is right, this environment cannot reach "
                         "the bulk export endpoint — use a personal API token, or download "
                         "the games and upload them.",
                    download_url=download_url,
                ) from exc
            if exc.code == 429:
                raise IngestError(
                    "Lichess is rate limiting this export.",
                    hint="Wait a minute and try again.",
                ) from exc
            raise IngestError(f"Lichess returned HTTP {exc.code}.",
                              download_url=download_url) from exc
        except IngestError as exc:
            # transport failure from _get: keep the manual route visible
            raise IngestError(
                str(exc),
                hint=exc.hint or "Lichess may be rate limiting or unreachable. A personal API "
                                 "token usually helps, or download the games and upload them.",
                download_url=download_url,
            ) from exc
        text = raw.decode("utf-8", errors="replace")
        if not text.lstrip().startswith("[Event"):
            raise IngestError(
                "Lichess did not return PGN data.",
                hint="Use a personal API token, or download the games and upload them.",
                download_url=download_url,
            )
        result.requests += 1
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    count = _count_games(text)
    if not count:
        raise IngestError(
            f"No games matched for {opts.username} on Lichess.",
            hint="Widen the date range or the time controls, or turn off rated-only.",
            download_url=download_url,
        )
    result.games = count
    result.files.append(path)
    progress(f"  {count} games")
    return result


# ---------------------------------------------------------------------- entry point

def fetch_games(options: FetchOptions, progress: Progress | None = None) -> FetchResult:
    """Download `options.username`'s games into a per-user cache folder.

    Returns a FetchResult whose `pgn_dir` can be handed straight to `analyze`.
    Raises IngestError with a usable `hint` for anything the caller should show.
    """
    opts = options.normalised()
    say: Progress = progress or (lambda _msg: None)
    say(f"Fetching {opts.username} from {opts.provider} "
        f"({', '.join(opts.speeds)}{', rated only' if opts.rated_only else ''})")
    if opts.provider == "chesscom":
        result = _fetch_chesscom(opts, say)
    else:
        result = _fetch_lichess(opts, say)
    # Only the files this run selected should be analysed, so point the analysis at
    # them explicitly rather than at the whole cache folder.
    result.pgn_dir = _write_manifest(opts, result)
    say(f"{result.games} games ready ({result.requests} requests, "
        f"{result.cached_months} cached)")
    return result


def _write_manifest(opts: FetchOptions, result: FetchResult) -> str:
    """Link the selected months into a run folder and return it."""
    run_dir = _cache_path(opts, "_run")
    os.makedirs(run_dir, exist_ok=True)
    for stale in os.listdir(run_dir):
        os.remove(os.path.join(run_dir, stale))
    for src in result.files:
        dst = os.path.join(run_dir, os.path.basename(src))
        try:
            os.link(src, dst)
        except OSError:
            with open(src, encoding="utf-8") as fh_in, open(dst, "w", encoding="utf-8") as fh_out:
                fh_out.write(fh_in.read())
    return run_dir


# ------------------------------------------------------------------- profile lookup

def lookup_player(provider: str, username: str, *, timeout: float = 15.0) -> dict:
    """Confirm a username exists and return a small profile card.

    Cheap enough to call while the user types. Raises IngestError when the account
    cannot be found, so the dashboard can say so before starting a run.
    """
    opts = FetchOptions(provider=provider, username=username).normalised()
    if opts.provider == "chesscom":
        base = f"https://api.chess.com/pub/player/{urllib.parse.quote(opts.username.lower())}"
        try:
            profile = json.loads(_get(base, timeout=timeout, accept="application/json", retries=2))
            stats = json.loads(_get(base + "/stats", timeout=timeout,
                                    accept="application/json", retries=2))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise IngestError(f"No Chess.com account called {opts.username}.") from exc
            raise IngestError(f"Chess.com returned HTTP {exc.code}.") from exc
        ratings = {}
        for key, label in (("chess_bullet", "bullet"), ("chess_blitz", "blitz"),
                           ("chess_rapid", "rapid"), ("chess_daily", "daily")):
            entry = stats.get(key) or {}
            rating = (entry.get("last") or {}).get("rating")
            if rating:
                ratings[label] = int(rating)
        return {
            "provider": "chesscom",
            "username": profile.get("username") or opts.username,
            "name": profile.get("name") or "",
            "title": profile.get("title") or "",
            "country": (profile.get("country") or "").rsplit("/", 1)[-1],
            "avatar": profile.get("avatar") or "",
            "url": profile.get("url") or f"https://www.chess.com/member/{opts.username}",
            "ratings": ratings,
        }

    url = f"https://lichess.org/api/user/{urllib.parse.quote(opts.username)}"
    try:
        profile = json.loads(_get(url, timeout=timeout, accept="application/json", retries=2))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise IngestError(f"No Lichess account called {opts.username}.") from exc
        raise IngestError(f"Lichess returned HTTP {exc.code}.") from exc
    perfs = profile.get("perfs") or {}
    ratings = {
        label: int(perfs[key]["rating"])
        for key, label in (("bullet", "bullet"), ("blitz", "blitz"), ("rapid", "rapid"),
                           ("classical", "classical"), ("correspondence", "daily"))
        if isinstance(perfs.get(key), dict) and perfs[key].get("rating")
        and (perfs[key].get("games") or 0) > 0
    }
    return {
        "provider": "lichess",
        "username": profile.get("username") or opts.username,
        "name": (profile.get("profile") or {}).get("realName") or "",
        "title": profile.get("title") or "",
        "country": (profile.get("profile") or {}).get("flag") or "",
        "avatar": "",
        "url": profile.get("url") or f"https://lichess.org/@/{opts.username}",
        "ratings": ratings,
    }


def provider_label(provider: str) -> str:
    return {"chesscom": "Chess.com", "lichess": "Lichess"}.get(provider, provider)


def speeds_from_csv(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if not value:
        return ("blitz", "rapid", "classical")
    items = value.split(",") if isinstance(value, str) else list(value)
    return tuple(s.strip().lower() for s in items if s.strip())
