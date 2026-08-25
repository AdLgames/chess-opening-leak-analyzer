"""Who may call the API, and how often."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.guard import (  # noqa: E402
    RateLimiter, allowed_origins, client_key,
)


# ---------------- Origins ----------------
def test_localhost_is_allowed_by_default():
    origins = allowed_origins("")
    assert "http://localhost:8080" in origins
    assert "http://127.0.0.1:8000" in origins


def test_a_page_from_anywhere_else_is_not():
    """The old default answered every origin, so any tab could read the local API."""
    assert "https://example.com" not in allowed_origins("")
    assert "*" not in allowed_origins("")


def test_opening_the_file_from_disk_still_works():
    """file:// sends a null origin; the README's no-server path depends on it."""
    assert "null" in allowed_origins("")


def test_an_operator_can_name_their_own_origin():
    origins = allowed_origins("https://leaks.example.com")
    assert "https://leaks.example.com" in origins
    assert "http://localhost:8080" in origins, "naming one does not drop the defaults"


def test_a_trailing_slash_does_not_create_an_origin_that_never_matches():
    assert "https://leaks.example.com" in allowed_origins("https://leaks.example.com/")


def test_wildcard_remains_available_but_has_to_be_asked_for():
    assert allowed_origins("*") == ["*"]


def test_no_origin_is_listed_twice():
    origins = allowed_origins("http://localhost:8080,https://a.example")
    assert len(origins) == len(set(origins))


# ---------------- Rate limiting ----------------
def test_requests_under_the_limit_are_allowed():
    rl = RateLimiter(limit=3, window_seconds=60)
    assert [rl.check("a", now=0)[0] for _ in range(3)] == [True, True, True]


def test_the_one_over_the_limit_is_refused():
    rl = RateLimiter(limit=2, window_seconds=60)
    rl.check("a", now=0)
    rl.check("a", now=0)
    allowed, retry_after = rl.check("a", now=0)
    assert allowed is False
    assert retry_after == 60


def test_the_window_reopens():
    rl = RateLimiter(limit=1, window_seconds=60)
    assert rl.check("a", now=0)[0] is True
    assert rl.check("a", now=30)[0] is False
    assert rl.check("a", now=61)[0] is True


def test_one_caller_does_not_spend_anothers_budget():
    rl = RateLimiter(limit=1, window_seconds=60)
    assert rl.check("a", now=0)[0] is True
    assert rl.check("b", now=0)[0] is True, "b has its own window"


def test_retry_after_counts_down_within_the_window():
    rl = RateLimiter(limit=1, window_seconds=60)
    rl.check("a", now=0)
    assert rl.check("a", now=45)[1] == 15


def test_retry_after_is_never_zero():
    """A Retry-After of 0 invites an immediate retry, which is the opposite of the point."""
    rl = RateLimiter(limit=1, window_seconds=60)
    rl.check("a", now=0)
    assert rl.check("a", now=59.9)[1] >= 1


# ---------------- Identifying the caller ----------------
def test_the_caller_is_their_address():
    assert client_key("10.0.0.4") == "10.0.0.4"


def test_a_forwarded_header_is_ignored_unless_the_operator_trusts_the_proxy(monkeypatch):
    """X-Forwarded-For is set by the caller. Believing it by default would let anyone
    mint a fresh rate-limit budget per request."""
    monkeypatch.delenv("LEAKLAB_TRUST_PROXY", raising=False)
    assert client_key("10.0.0.4", "1.2.3.4") == "10.0.0.4"

    monkeypatch.setenv("LEAKLAB_TRUST_PROXY", "1")
    assert client_key("10.0.0.4", "1.2.3.4") == "1.2.3.4"


def test_the_first_hop_is_the_client_when_the_proxy_is_trusted(monkeypatch):
    monkeypatch.setenv("LEAKLAB_TRUST_PROXY", "1")
    assert client_key("10.0.0.4", "1.2.3.4, 10.0.0.1") == "1.2.3.4"


def test_an_unknown_caller_still_gets_a_key():
    assert client_key(None) == "unknown"
