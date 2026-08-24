"""Ingestion tests. No network: `_get` is replaced with a fixture responder."""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chessopening import ingest  # noqa: E402
from chessopening.ingest import FetchOptions, IngestError, fetch_games  # noqa: E402

GAME = """[Event "Live Chess"]
[Site "Chess.com"]
[White "alice"]
[Black "bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""


def month_payload(*, count: int, rated: bool = True, time_class: str = "blitz",
                  end: int | None = None) -> bytes:
    end = end or int(dt.datetime(2026, 7, 15, tzinfo=dt.timezone.utc).timestamp())
    games = [{
        "rules": "chess",
        "rated": rated,
        "time_class": time_class,
        "end_time": end,
        "pgn": GAME,
    } for _ in range(count)]
    return json.dumps({"games": games}).encode()


@pytest.fixture()
def responder(monkeypatch):
    """Route ingest's HTTP through a dict of url-substring -> bytes | Exception."""
    calls: list[str] = []
    routes: dict[str, object] = {}

    def fake_get(url, *, timeout, accept, token=None, retries=3):
        calls.append(url)
        for needle, value in routes.items():
            if needle in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise AssertionError(f"no fixture for {url}")

    monkeypatch.setattr(ingest, "_get", fake_get)
    return type("R", (), {"routes": routes, "calls": calls})()


def opts(tmp_path, **kw) -> FetchOptions:
    base = dict(provider="chesscom", username="alice", cache_dir=str(tmp_path))
    base.update(kw)
    return FetchOptions(**base)


def test_chesscom_walks_months_newest_first_and_stops_at_the_cap(responder, tmp_path):
    responder.routes["games/archives"] = json.dumps({"archives": [
        "https://api.chess.com/pub/player/alice/games/2026/05",
        "https://api.chess.com/pub/player/alice/games/2026/06",
    ]}).encode()
    responder.routes["2026/06"] = month_payload(count=3)
    responder.routes["2026/05"] = month_payload(count=3)

    res = fetch_games(opts(tmp_path, max_games=4))

    assert res.games == 4
    assert res.months == ["2026/06", "2026/05"]     # newest month first
    assert res.provider == "chesscom"
    assert len(os.listdir(res.pgn_dir)) == 2


def test_chesscom_filters_unrated_and_other_time_classes(responder, tmp_path):
    responder.routes["games/archives"] = json.dumps({
        "archives": ["https://api.chess.com/pub/player/alice/games/2026/06"]}).encode()
    payload = json.loads(month_payload(count=1).decode())
    payload["games"] += json.loads(month_payload(count=1, rated=False).decode())["games"]
    payload["games"] += json.loads(month_payload(count=1, time_class="bullet").decode())["games"]
    responder.routes["2026/06"] = json.dumps(payload).encode()

    res = fetch_games(opts(tmp_path, speeds=("blitz",), rated_only=True))
    assert res.games == 1


def test_chesscom_date_window_skips_months_outside_it(responder, tmp_path):
    responder.routes["games/archives"] = json.dumps({"archives": [
        "https://api.chess.com/pub/player/alice/games/2026/04",
        "https://api.chess.com/pub/player/alice/games/2026/05",
        "https://api.chess.com/pub/player/alice/games/2026/06",
    ]}).encode()
    responder.routes["2026/05"] = month_payload(
        count=2, end=int(dt.datetime(2026, 5, 20, tzinfo=dt.timezone.utc).timestamp()))

    res = fetch_games(opts(tmp_path, since="2026-05-01", until="2026-05-31"))
    assert res.months == ["2026/05"] and res.games == 2
    assert not any("2026/06" in c or "2026/04" in c for c in responder.calls)


def test_second_run_reuses_the_cached_month(responder, tmp_path):
    responder.routes["games/archives"] = json.dumps({
        "archives": ["https://api.chess.com/pub/player/alice/games/2026/06"]}).encode()
    responder.routes["2026/06"] = month_payload(count=2)

    first = fetch_games(opts(tmp_path))
    calls_after_first = len(responder.calls)
    second = fetch_games(opts(tmp_path))

    assert second.games == first.games == 2
    assert second.cached_months == 1
    # only the archive list is requested again, never the month itself
    assert len(responder.calls) == calls_after_first + 1


def test_missing_chesscom_player_gets_an_actionable_error(responder, tmp_path):
    responder.routes["games/archives"] = urllib.error.HTTPError(
        "u", 404, "Not Found", {}, None)  # type: ignore[arg-type]
    with pytest.raises(IngestError) as err:
        fetch_games(opts(tmp_path, username="nobodyhere"))
    assert "no player" in str(err.value).lower()
    assert err.value.hint


def test_lichess_export_is_written_and_counted(responder, tmp_path):
    responder.routes["lichess.org/api/games/user"] = (GAME + "\n" + GAME).encode()
    res = fetch_games(opts(tmp_path, provider="lichess", username="alice"))
    assert res.provider == "lichess" and res.games == 2


def test_lichess_401_explains_the_token_and_offers_a_download(responder, tmp_path):
    responder.routes["lichess.org/api/games/user"] = urllib.error.HTTPError(
        "u", 401, "Unauthorized", {}, None)  # type: ignore[arg-type]
    with pytest.raises(IngestError) as err:
        fetch_games(opts(tmp_path, provider="lichess"))
    assert "token" in err.value.hint.lower()
    assert err.value.download_url.endswith("/download")


def test_lichess_non_pgn_body_is_rejected(responder, tmp_path):
    responder.routes["lichess.org/api/games/user"] = b"<!DOCTYPE html><html>404</html>"
    with pytest.raises(IngestError) as err:
        fetch_games(opts(tmp_path, provider="lichess"))
    assert "did not return pgn" in str(err.value).lower()


@pytest.mark.parametrize("bad", ["", "a", "has space", "way" * 30, "semi;colon"])
def test_bad_usernames_are_refused_before_any_request(responder, tmp_path, bad):
    with pytest.raises(IngestError):
        fetch_games(opts(tmp_path, username=bad))
    assert responder.calls == []


def test_unknown_provider_is_refused(tmp_path):
    with pytest.raises(IngestError):
        fetch_games(FetchOptions(provider="fide", username="alice", cache_dir=str(tmp_path)))


def test_bad_date_is_refused(responder, tmp_path):
    with pytest.raises(IngestError):
        fetch_games(opts(tmp_path, since="15/05/2026"))
