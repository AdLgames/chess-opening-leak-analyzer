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

import json
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
        # Appended, never inserted: `vercel/` can hold a prepare.py-built bundle
        # with its own copy of `chessopening`, and putting it first would have
        # the rest of the suite silently testing that stale copy instead.
        sys.path.append(VERCEL)
    os.environ["POSTGRES_URL"] = URL
    try:
        import pg8000.dbapi  # noqa: F401, PLC0415
        from accounts import auth, db, state  # noqa: F401, PLC0415
        from fastapi.testclient import TestClient  # noqa: F401, PLC0415
    except ImportError:
        return None
    return auth, db, state, TestClient


LOADED = _load()
SKIP_REASON = ("needs LEAKLAB_TEST_DATABASE_URL and pg8000 + fastapi installed"
               if LOADED is None else "")

try:                                   # pragma: no cover - only for a direct run
    import pytest

    # Marked rather than returned early: a test that quietly does nothing and
    # reports "passed" is worse than no test, because it claims cover it has not
    # got. Under pytest these show up as skipped, by name, with the reason.
    pytestmark = pytest.mark.skipif(LOADED is None, reason=SKIP_REASON)
except ImportError:
    pytest = None


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
    _auth, db, _state, _tc = LOADED
    # The first call has to create the pool *and* use it. A single lock across
    # both would hang here forever rather than failing, which is why this is a
    # test and not a code reading.
    db.ensure_schema()
    db.ensure_schema()
    applied = [r["id"] for r in db.query("SELECT id FROM schema_migrations ORDER BY id")]
    assert applied == [name for name, _ in db.MIGRATIONS]


def test_a_leak_opens_drills_closes_and_can_come_back():
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


def _tree(key: str, *, games: list[int], score: float, book: float,
          opening: str = "Scandinavian Defence") -> dict:
    return {"key": key, "position": "epd", "fen": f"fen-{key}", "player_color": "white",
            "eco": "B01", "opening": opening, "variation_line": "e4 d5 exd5",
            "your_move": "exd5", "move_number": 2, "your_score_pct": score,
            "db_move_score_pct": book, "db_position_score_pct": book,
            "in_book": "yes", "game_idx": games}


def _run_with_tree(client, run_id, at, tree, game_ids):
    return client.post("/api/state/run", json={
        "run": {"id": run_id, "at": at, "player": "tester", "games": len(game_ids),
                "leaks": 0, "cost": 0},
        "leaks": [], "tree": tree, "game_ids": game_ids})


def test_evidence_adds_up_across_runs_that_read_different_games():
    """The rare-line blind spot, closed.

    Two games a month never reaches the threshold inside one run. Across three
    runs over different games it does, and the line finally becomes a leak.
    """
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, uid = _client(auth, db, state, TestClient)

    for i, run_id in enumerate(("r1", "r2")):
        games = [f"g{i}a", f"g{i}b"]
        out = _run_with_tree(client, run_id, 1700000000000 + i,
                             [_tree("rare", games=[0, 1], score=0.0, book=55.0)], games)
        assert out.status_code == 200, out.text
        promoted = out.json()["promoted"]
        if i == 0:
            assert promoted == [], "two games is not enough to judge"

    progress = client.get("/api/state/progress").json()
    row = next(r for r in progress["accumulated"] if r["key"] == "rare")
    assert row["games"] == 4, "the two runs' games were not added up"
    assert row["promoted"] is True
    # and it is a real leak now, marked as one nobody's single run could see
    assert any(leak["key"] == "rare" for leak in progress["leaks"])
    source = db.query_one("SELECT source, games FROM leaks"
                          " WHERE user_id = %s AND leak_key = 'rare'", (uid,))
    assert source["source"] == "accumulated" and source["games"] == 4


def test_re_reading_the_same_games_does_not_inflate_the_count():
    """The reason evidence is per game and not a tally.

    "Your last 120 games" run twice in a week is mostly the same games. A count
    would have doubled; a set of (decision, game) pairs cannot.
    """
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, _uid = _client(auth, db, state, TestClient)
    games = ["same1", "same2"]

    _run_with_tree(client, "r1", 1700000000000,
                   [_tree("dup", games=[0, 1], score=0.0, book=55.0)], games)
    _run_with_tree(client, "r2", 1700100000000,
                   [_tree("dup", games=[0, 1], score=0.0, book=55.0)], games)

    row = next(r for r in client.get("/api/state/progress").json()["accumulated"]
               if r["key"] == "dup")
    assert row["games"] == 2, "the same two games were counted twice"
    assert row["promoted"] is False, "two games must not clear the threshold"


def test_a_partly_overlapping_window_counts_only_what_is_new():
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, _uid = _client(auth, db, state, TestClient)

    _run_with_tree(client, "r1", 1700000000000,
                   [_tree("roll", games=[0, 1], score=0.0, book=55.0)], ["a", "b"])
    # the next run's window has slid: one game in common, one new
    _run_with_tree(client, "r2", 1700100000000,
                   [_tree("roll", games=[0, 1], score=0.0, book=55.0)], ["b", "c"])

    row = next(r for r in client.get("/api/state/progress").json()["accumulated"]
               if r["key"] == "roll")
    assert row["games"] == 3, f"expected a, b, c — got {row['games']}"
    assert row["promoted"] is True


def test_a_line_that_matches_the_book_never_gets_promoted():
    """Accumulating evidence must not mean accumulating accusations."""
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, _uid = _client(auth, db, state, TestClient)
    for i in range(3):
        _run_with_tree(client, f"r{i}", 1700000000000 + i,
                       [_tree("fine", games=[0], score=56.0, book=55.0)], [f"g{i}"])

    progress = client.get("/api/state/progress").json()
    row = next(r for r in progress["accumulated"] if r["key"] == "fine")
    assert row["games"] == 3 and row["promoted"] is False
    assert not any(leak["key"] == "fine" for leak in progress["leaks"])


def test_the_pooled_score_is_weighted_by_games_not_by_runs():
    if not LOADED:
        return
    auth, db, state, TestClient = LOADED  # noqa: N806
    client, _uid = _client(auth, db, state, TestClient)
    # four games at 0%, then one at 100%: the pooled score is 20%, not 50%
    _run_with_tree(client, "r1", 1700000000000,
                   [_tree("pool", games=[0, 1, 2, 3], score=0.0, book=50.0)],
                   ["p1", "p2", "p3", "p4"])
    _run_with_tree(client, "r2", 1700100000000,
                   [_tree("pool", games=[0], score=100.0, book=50.0)], ["p5"])

    row = next(r for r in client.get("/api/state/progress").json()["accumulated"]
               if r["key"] == "pool")
    assert row["games"] == 5
    assert row["scorePct"] == 20.0, row["scorePct"]


def test_export_is_complete_and_delete_leaves_nothing():
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
    # the accumulation record is part of "everything we hold", not an exception
    for key in ("decisions", "decision_games", "run_games"):
        assert key in payload

    assert client.post("/api/auth/delete", json={}).status_code == 400   # confirmation
    assert client.post("/api/auth/delete", json={"confirm": "DELETE"}).status_code == 200
    for table in ("runs", "leaks", "repertoire_commits", "drill_schedule", "drill_attempts",
                  "user_prefs", "last_reports", "sessions", "linked_accounts"):
        left = db.query_one(f"SELECT count(*) AS n FROM {table} WHERE user_id = %s", (uid,))
        assert int(left["n"]) == 0, f"{table} survived the deletion"
    assert db.query_one("SELECT count(*) AS n FROM users WHERE id = %s", (uid,))["n"] == 0


def test_a_storage_integration_prefix_still_resolves():
    """Vercel can prefix every variable a storage integration injects.

    A prefixed deployment has `<PREFIX>_POSTGRES_URL` and nothing named
    plainly, which read as "no database configured" while every variable was
    present and correct. Matching the suffix fixes that without this code
    having to know the prefix.
    """
    auth, db, state, TestClient = _load()
    saved = {k: os.environ[k] for k in list(os.environ)
             if k == "POSTGRES_PRISMA_URL" or k.endswith(("POSTGRES_URL", "DATABASE_URL"))}

    def only(env):
        for k in list(os.environ):
            if k in db.URL_NAMES or k.endswith(tuple(f"_{n}" for n in db.URL_NAMES)):
                del os.environ[k]
        os.environ.update(env)
        return db.resolve_url()

    try:
        assert only({"CHESS_POSTGRES_URL": "u"})[0] == "CHESS_POSTGRES_URL"
        # An exact name is still the answer when both are present.
        assert only({"CHESS_POSTGRES_URL": "p", "POSTGRES_URL": "b"})[0] == "POSTGRES_URL"
        # Pooled first: a serverless function opens a connection per invocation.
        assert only({"CHESS_POSTGRES_URL": "u"})[0] == "CHESS_POSTGRES_URL"
        # The unpooled endpoint must never be mistaken for the pooled one.
        assert only({"CHESS_POSTGRES_URL_NON_POOLING": "u"}) is None
        # `_DATABASE_URL` is deliberately NOT scanned for: the tail is too common
        # to claim. This module's own test variable is the proof — an earlier
        # draft matched it, and a stray OLD_DATABASE_URL would have pointed a
        # live deployment at the wrong database just as easily.
        assert only({"LEAKLAB_TEST_DATABASE_URL": "u"}) is None
        assert only({"CHESS_DATABASE_URL": "u"}) is None
        assert only({"CHESS_POSTGRES_URL": "   ", "CHESS_DATABASE_URL": "u"}) is None
        assert only({}) is None
    finally:
        for k in list(os.environ):
            if k in db.URL_NAMES or k.endswith(tuple(f"_{n}" for n in db.URL_NAMES)):
                del os.environ[k]
        os.environ.update(saved)
    # The restore has to leave the rest of this module able to reach Postgres.
    assert db.configured() is True


def test_diagnosis_separates_the_two_ways_accounts_stay_off():
    """`configured()` says no; `diagnosis()` has to say which no.

    The only view of a deployment is often a phone browser, where one False is
    not enough to act on: a missing connection string and a missing driver need
    opposite fixes. The report must also stay safe to serve publicly, so the
    connection string itself is never allowed to appear in it.
    """
    auth, db, state, TestClient = _load()

    good = db.diagnosis()
    assert good["url_env"] in ("POSTGRES_PRISMA_URL", "POSTGRES_URL", "DATABASE_URL")
    assert good["driver"] is True
    assert good["connect"] == "ok"
    assert URL not in json.dumps(good)

    saved = {n: os.environ.pop(n) for n in
             ("POSTGRES_PRISMA_URL", "POSTGRES_URL", "DATABASE_URL") if n in os.environ}
    try:
        blind = db.diagnosis()
        assert blind["url_env"] is None
        # Not "failed": nothing was dialled, so nothing can be said about reachability.
        assert blind["connect"] == "not attempted"
        assert db.configured() is False
    finally:
        os.environ.update(saved)


if __name__ == "__main__":
    if not LOADED:
        raise SystemExit(f"skipped: {SKIP_REASON}")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
