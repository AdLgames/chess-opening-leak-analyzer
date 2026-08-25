"""Who may call the local API, and how often.

The server binds 0.0.0.0 and answered `allow_origins=["*"]` with no throttle anywhere.
On a laptop that is mostly harmless; on a shared network it means any page the user has
open in another tab can read their game history out of the local API, and any script can
start unbounded analysis jobs. Neither is what "runs locally" is supposed to mean.

Two small pieces, kept out of the server module so they can be tested without standing a
server up:

* `allowed_origins()` — the browser origins the API answers to, which is localhost by
  default and whatever the operator names when they deploy it somewhere real.
* `RateLimiter` — a fixed-window counter per client, so a runaway script gets 429s
  instead of a queue of analysis jobs. Deliberately in-process and approximate: the
  point is to bound accidents, not to survive an adversary with a botnet.
"""
from __future__ import annotations

import os
import threading
import time

# The ports the dashboard is served from in development: the static server, the API
# itself, and the two Vite/Next defaults people reach for when they fork it.
LOCAL_PORTS = (8080, 8000, 5173, 3000, 4173)
LOCAL_HOSTS = ("localhost", "127.0.0.1")


def allowed_origins(extra: str | None = None) -> list[str]:
    """Origins the API will answer. Localhost by default; `LEAKLAB_ORIGINS` adds more.

    `LEAKLAB_ORIGINS="*"` restores the old behaviour for anyone who genuinely wants it —
    an explicit opt-in rather than the default nobody chose.
    """
    raw = extra if extra is not None else os.environ.get("LEAKLAB_ORIGINS", "")
    named = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    if "*" in named:
        return ["*"]
    local = [
        f"{scheme}://{host}:{port}"
        for scheme in ("http", "https")
        for host in LOCAL_HOSTS
        for port in LOCAL_PORTS
    ]
    # Opening index.html straight off disk gives a null origin; keeping it means the
    # "no server needed" path in the README still works.
    return [*dict.fromkeys([*local, "null", *named])]


class RateLimiter:
    """Fixed-window request counting, per client key.

    A fixed window can let through up to 2x the limit across a window boundary. That is
    a real property of the algorithm and it is the right trade here: the alternative
    (a sliding log) costs memory per request to defend against something this is not
    trying to defend against.
    """

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> tuple[bool, int]:
        """(allowed, seconds until the window resets)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            started, count = self._hits.get(key, (now, 0))
            if now - started >= self.window:
                started, count = now, 0
            retry_after = max(1, int(self.window - (now - started)))
            if count >= self.limit:
                self._hits[key] = (started, count)
                return False, retry_after
            self._hits[key] = (started, count + 1)
            return True, retry_after

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


def client_key(host: str | None, forwarded_for: str | None = None) -> str:
    """Identify the caller.

    `X-Forwarded-For` is only consulted when the operator has said they are behind a
    proxy: taken on trust it is a header the caller controls, so it would turn the
    limiter into something anyone can walk straight past.
    """
    if forwarded_for and os.environ.get("LEAKLAB_TRUST_PROXY") == "1":
        return forwarded_for.split(",")[0].strip() or (host or "unknown")
    return host or "unknown"
