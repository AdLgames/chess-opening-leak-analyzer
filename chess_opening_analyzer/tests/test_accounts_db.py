"""The progress API against a real Postgres.

The leak lifecycle is the whole point of accounts, and it lives in SQL, so
asserting it against anything other than a database would be asserting a mock.
This module runs when `LEAKLAB_TEST_DATABASE_URL` points at a throwaway
Postgres — CI provides one as a service container — and skips otherwise, so a
checkout with no database still runs the rest of the suite.

It also pins the two failures that are invisible until something really
connects: the first request on a cold start must not deadlock, and deleting an
account must leave nothing behind.
"""
from __future__ import annotations

import base64
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERCEL = os.path.join(ROOT, "vercel")
URL = os.environ.get("LEAKLAB_TEST_DATABASE_URL", "").strip()


def _load():
    """Import the accounts package, or return None if this host cannot."""
    if not URL:
        return None
    if VERCEL not in sys.path:
        sys.path.insert(0, VERCEL)
    os.environ["POSTGRES_URL"] = URL
    os.environ.setdefault("LEAKLAB_ENCRYPTION_KEY",
                          base64.urlsafe_b64encode(os.urandom(32)).decode())
    try:
        import psycopg  # noqa: F401, PLC0415
        from accounts import auth, db, state  # noqa: F401, PLC0415
        from fastapi.testclient import TestClient  # noqa: F401, PLC0415
    except ImportError:
        return None
    return auth, db, state, TestClient


LOADED = _load()


def _app(auth, state):
    """Just the account routers.

    Mounting these rather than importing `api/index.py` keeps the test off the
    analyser: python-chess and the engine have nothing to do with whether a
    leak's status moves correctly.
    """
    from fastapi import FastAPI  # noqa: PLC0415

    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(state.router)
    return app


def _client(auth, db, state, TestClient):  # noqa: N803 - the class keeps its own name
    """A signed-in client on a fresh user, with the schema applied."""
    db.ensure_schema()
    uid = str(uuid.uuid4())
    db.execute("INSERT INTO users (id, email, display_name) VALUES (%s, %s, %s)",
               (uid, f"{uid}@example.test", "tester"))
    token = auth.crypto.new_token()
    db.execute("INSERT INTO sessions (token_hash, user_id, expires_at)"
               " VALUES (%s, %s, now() + interval '1 day')",
               (auth.crypto.hash_token(token), uid))
    client = TestClient(_app(auth, state))
    client.cookies.set(auth.COOKIE, token)
    return client, uid


def _leak(key: str, cost: float) -> dict:
    return {"key": key, "position": "epd", "fen": "fen", "color": "white", "eco": "C50",
            "opening": "Italian Game", "played": "Bc4", "moveNumber": 4, "cost": cost,
            "games": 9, "flag": "blunder"}


def _run(client, run_id: str, at: int, leaks: list[dict]):
    return client.post("/api/state/run", json={
        "run": {"id": run_id, "at": at, "player": "tester", "games": 100,
                "leaks": len(leaks), "cost": sum(l["cost"] for l in leaks)},
        "leaks": leaks})


def test_schema_applies_and_replays_without_deadlocking():
    if not LOADED:
        return
    _auth, db, _state, _tc = LOADED
    # The first call has to create the pool *and* use it. A single lock across
    # both would hang here forever rather than failing, which is why this is a
    # test and not a code reading.
    db.ensure_schema()
    db.ensure_schema()
    applied = [r["id"] for r in db.query("SELECT id FROM schema_migrations ORDER BY id")]
    assert applied == [name for name, _ in db.MIGRATIONS]


def test_a_leak_opens_drills_closes_and_can_come_back():
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, _uid = _client(auth, db, state, TestClient)

    assert _run(client, "r1", 1700000000000, [_leak("a", 6.0), _leak("b", 3.0)]).status_code == 200
    assert client.get("/api/state/progress").json()["counts"]["open"] == 2

    # Committing a reply is the moment a leak stops being merely known about.
    client.post("/api/state/repertoire", json={"entry": {
        "key": "a", "status": "committed", "answer": "d3", "line": ["e4", "e5"]}})
    counts = client.get("/api/state/progress").json()["counts"]
    assert (counts["open"], counts["drilling"]) == (1, 1)

    # A run that no longer finds it is what closes it — not the user saying so.
    _run(client, "r2", 1700100000000, [_leak("b", 3.0)])
    assert client.get("/api/state/progress").json()["counts"]["fixed"] == 1

    # And a later run that finds it again is a regression, not a new leak.
    _run(client, "r3", 1700200000000, [_leak("a", 5.0), _leak("b", 3.0)])
    counts = client.get("/api/state/progress").json()["counts"]
    assert counts["regressed"] == 1 and counts["fixed"] == 0


def test_drills_accumulate_and_schedule_forward():
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, _uid = _client(auth, db, state, TestClient)
    _run(client, "r1", 1700000000000, [_leak("x", 4.0)])
    for correct in (True, True, False):
        client.post("/api/state/drill", json={"key": "x", "correct": correct, "label": "Italian"})
    drill = client.get("/api/state").json()["drills"]["x"]
    assert (drill["right"], drill["wrong"], drill["streak"]) == (2, 1, 0)
    assert drill["due"] > 0
    # Drilling a leak moves it on too, even without a repertoire decision.
    assert client.get("/api/state/progress").json()["counts"]["drilling"] == 1


def test_signing_in_adopts_what_the_browser_already_had():
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, _uid = _client(auth, db, state, TestClient)
    _run(client, "r1", 1700000000000, [_leak("y", 4.0)])
    for correct in (True, True):
        client.post("/api/state/drill", json={"key": "y", "correct": correct})

    # A longer local history must win over the shorter server one, not be lost.
    client.post("/api/state/import", json={
        "repertoire": [{"key": "z", "status": "committed", "answer": "Nf3"}],
        "runs": [{"id": "old", "at": 1690000000000, "player": "tester", "games": 20}],
        "drills": {"y": {"right": 9, "wrong": 0, "streak": 4, "last": 1690000000000,
                         "due": 1690100000000}},
        "prefs": {"theme": "dark"}})
    st = client.get("/api/state").json()
    assert st["drills"]["y"]["right"] == 9
    assert st["prefs"]["theme"] == "dark"
    assert {e["key"] for e in st["repertoire"]} == {"z"}
    assert {r["id"] for r in st["runs"]} == {"r1", "old"}


def test_export_is_complete_and_delete_leaves_nothing():
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, uid = _client(auth, db, state, TestClient)
    _run(client, "r1", 1700000000000, [_leak("q", 4.0)])
    client.post("/api/state/repertoire", json={"entry": {"key": "q", "status": "committed",
                                                         "answer": "d3"}})
    client.post("/api/state/drill", json={"key": "q", "correct": True})
    client.post("/api/state/pref", json={"key": "theme", "value": "light"})

    payload = client.get("/api/auth/export").json()
    assert payload["runs"] and payload["leaks"] and payload["repertoire"]
    assert payload["drill_attempts"] and payload["prefs"]

    assert client.post("/api/auth/delete", json={}).status_code == 400   # confirmation
    assert client.post("/api/auth/delete", json={"confirm": "DELETE"}).status_code == 200
    for table in ("runs", "leaks", "repertoire_commits", "drill_schedule", "drill_attempts",
                  "user_prefs", "last_reports", "sessions", "linked_accounts"):
        left = db.query_one(f"SELECT count(*) AS n FROM {table} WHERE user_id = %s", (uid,))
        assert int(left["n"]) == 0, f"{table} survived the deletion"
    assert db.query_one("SELECT count(*) AS n FROM users WHERE id = %s", (uid,))["n"] == 0


if __name__ == "__main__":
    if not LOADED:
        raise SystemExit(
            "skipped: set LEAKLAB_TEST_DATABASE_URL and install psycopg + fastapi")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
