#!/usr/bin/env python3
"""Postgres access for the hosted deployment.

The analyser itself is still stateless — this module exists only so a signed-in
user's progress against their leaks survives the run that found them.

Connection handling is shaped by the serverless runtime: a function instance may
serve many requests but is also thrown away without warning, so connections come
from a small per-instance pool opened lazily and every statement runs inside a
short transaction. `POSTGRES_URL` is what Vercel Postgres (Neon) injects; the
pooled URL is the right one here because instances are numerous and short-lived.

The schema is applied by `ensure_schema()` on first use of an instance. Every
statement is `IF NOT EXISTS`, and `schema_migrations` records what has run, so
concurrent cold starts racing each other is harmless.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Iterator

_POOL: Any = None
# Two locks, not one: `ensure_schema` needs a connection, so a single lock held
# across both would deadlock the first request on every cold start.
_POOL_LOCK = threading.Lock()
_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False


class DatabaseUnavailable(RuntimeError):
    """No database is configured, or it cannot be reached."""


def database_url() -> str | None:
    """The connection string, preferring the pooled endpoint."""
    for name in ("POSTGRES_PRISMA_URL", "POSTGRES_URL", "DATABASE_URL"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def driver_available() -> bool:
    """Whether this deployment can actually talk to Postgres.

    A URL is not enough: the driver has to be installed too. Checking both is
    what lets the rest of the app treat "no accounts" as a state rather than as
    a crash — a deployment missing either one serves the analyser exactly as it
    did before accounts existed, instead of 500ing on every request.
    """
    try:
        import psycopg_pool  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def configured() -> bool:
    return database_url() is not None and driver_available()


def _pool() -> Any:
    global _POOL  # noqa: PLW0603 - one pool per function instance, by design
    if _POOL is not None:
        return _POOL
    url = database_url()
    if not url:
        raise DatabaseUnavailable(
            "No POSTGRES_URL is set. Accounts need a database — see vercel/README.md.")
    with _POOL_LOCK:
        if _POOL is None:
            try:
                from psycopg_pool import ConnectionPool  # noqa: PLC0415
            except ImportError as exc:  # pragma: no cover - deployment error
                raise DatabaseUnavailable(f"psycopg is not installed: {exc}") from exc
            # A function instance handles a handful of concurrent requests at most;
            # a big pool would only starve the database of connections.
            _POOL = ConnectionPool(url, min_size=0, max_size=4, timeout=10.0,
                                   kwargs={"autocommit": False}, open=True)
    return _POOL


@contextmanager
def connection() -> Iterator[Any]:
    """A pooled connection with the schema in place, committed on clean exit."""
    ensure_schema()
    with _pool().connection() as con:
        yield con


@contextmanager
def cursor(row_factory: str = "dict") -> Iterator[Any]:
    """A cursor that yields dicts by default, since callers build JSON."""
    from psycopg.rows import dict_row, tuple_row  # noqa: PLC0415

    with connection() as con:
        with con.cursor(row_factory=dict_row if row_factory == "dict" else tuple_row) as cur:
            yield cur


def query(sql: str, params: tuple | dict | None = None) -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall()) if cur.description else []


def query_one(sql: str, params: tuple | dict | None = None) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple | dict | None = None) -> None:
    with cursor() as cur:
        cur.execute(sql, params)


# --------------------------------------------------------------------- schema
# Ordered list of (id, statements). Never edit a migration that has shipped;
# add another one. The ids are recorded in schema_migrations.
MIGRATIONS: list[tuple[str, tuple[str, ...]]] = [
    (
        "0001_accounts",
        (
            """
            CREATE TABLE IF NOT EXISTS users (
                id            uuid PRIMARY KEY,
                email         text UNIQUE,
                display_name  text NOT NULL DEFAULT '',
                created_at    timestamptz NOT NULL DEFAULT now(),
                last_seen_at  timestamptz NOT NULL DEFAULT now()
            )
            """,
            # One row per identity the user can sign in with. There is no token
            # column: the Lichess access token is used once in the callback to
            # learn who signed in, and then dropped.
            """
            CREATE TABLE IF NOT EXISTS linked_accounts (
                provider          text NOT NULL,
                provider_user_id  text NOT NULL,
                user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                username          text NOT NULL DEFAULT '',
                scopes            text NOT NULL DEFAULT '',
                linked_at         timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (provider, provider_user_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS linked_accounts_user ON linked_accounts (user_id)",
            # Sessions are server-side so a sign-out is a real revocation; the
            # cookie carries a random token and the table keeps only its hash.
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash  text PRIMARY KEY,
                user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at  timestamptz NOT NULL DEFAULT now(),
                expires_at  timestamptz NOT NULL,
                user_agent  text NOT NULL DEFAULT ''
            )
            """,
            "CREATE INDEX IF NOT EXISTS sessions_user ON sessions (user_id)",
            "CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions (expires_at)",
            # Single-use email sign-in tokens, and the PKCE material for an
            # in-flight Lichess authorisation. Both are short-lived and swept.
            """
            CREATE TABLE IF NOT EXISTS login_tokens (
                token_hash  text PRIMARY KEY,
                email       text NOT NULL,
                created_at  timestamptz NOT NULL DEFAULT now(),
                expires_at  timestamptz NOT NULL,
                used_at     timestamptz
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS oauth_states (
                state        text PRIMARY KEY,
                verifier     text NOT NULL,
                redirect_to  text NOT NULL DEFAULT '/app/',
                created_at   timestamptz NOT NULL DEFAULT now(),
                expires_at   timestamptz NOT NULL
            )
            """,
        ),
    ),
    (
        "0002_progress",
        (
            # One row per completed analysis. Small by design: enough to plot
            # progress without keeping every report forever.
            """
            CREATE TABLE IF NOT EXISTS runs (
                id            text NOT NULL,
                user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ran_at        timestamptz NOT NULL DEFAULT now(),
                player        text NOT NULL DEFAULT '',
                source        text NOT NULL DEFAULT '',
                games         integer NOT NULL DEFAULT 0,
                leaks         integer NOT NULL DEFAULT 0,
                cost          double precision NOT NULL DEFAULT 0,
                summary       jsonb NOT NULL DEFAULT '{}'::jsonb,
                PRIMARY KEY (user_id, id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS runs_user_time ON runs (user_id, ran_at)",
            # The lifecycle of one leak, keyed on the position EPD plus the move
            # played — the same key the browser has always used, so nothing has
            # to be re-derived to migrate a user's existing local data.
            """
            CREATE TABLE IF NOT EXISTS leaks (
                user_id        uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                leak_key       text NOT NULL,
                position       text NOT NULL DEFAULT '',
                fen            text NOT NULL DEFAULT '',
                color          text NOT NULL DEFAULT '',
                eco            text NOT NULL DEFAULT '',
                opening        text NOT NULL DEFAULT '',
                played         text NOT NULL DEFAULT '',
                move_number    integer NOT NULL DEFAULT 0,
                status         text NOT NULL DEFAULT 'open',
                cost           double precision NOT NULL DEFAULT 0,
                first_cost     double precision NOT NULL DEFAULT 0,
                games          integer NOT NULL DEFAULT 0,
                flag           text NOT NULL DEFAULT '',
                first_seen_at  timestamptz NOT NULL DEFAULT now(),
                last_seen_at   timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, leak_key)
            )
            """,
            "CREATE INDEX IF NOT EXISTS leaks_user_status ON leaks (user_id, status)",
            # What the user decided to play instead, and whether they dismissed
            # the finding. One row per leak; the decision can change.
            """
            CREATE TABLE IF NOT EXISTS repertoire_commits (
                user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                leak_key    text NOT NULL,
                status      text NOT NULL DEFAULT 'committed',
                answer      text NOT NULL DEFAULT '',
                line        jsonb NOT NULL DEFAULT '[]'::jsonb,
                entry       jsonb NOT NULL DEFAULT '{}'::jsonb,
                decided_at  timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, leak_key)
            )
            """,
            # Spaced repetition: the running state the drill screen reads, plus
            # the append-only attempt log that makes progress auditable.
            """
            CREATE TABLE IF NOT EXISTS drill_schedule (
                user_id   uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                leak_key  text NOT NULL,
                label     text NOT NULL DEFAULT '',
                right_n   integer NOT NULL DEFAULT 0,
                wrong_n   integer NOT NULL DEFAULT 0,
                streak    integer NOT NULL DEFAULT 0,
                last_at   timestamptz,
                due_at    timestamptz,
                PRIMARY KEY (user_id, leak_key)
            )
            """,
            "CREATE INDEX IF NOT EXISTS drill_schedule_due ON drill_schedule (user_id, due_at)",
            """
            CREATE TABLE IF NOT EXISTS drill_attempts (
                id         bigserial PRIMARY KEY,
                user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                leak_key   text NOT NULL,
                correct    boolean NOT NULL,
                played     text NOT NULL DEFAULT '',
                at         timestamptz NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS drill_attempts_user ON drill_attempts (user_id, at)",
            """
            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                key      text NOT NULL,
                value    jsonb NOT NULL,
                PRIMARY KEY (user_id, key)
            )
            """,
            # The most recent report, so a new device opens on something real
            # rather than an empty screen. One row per user, replaced each run.
            """
            CREATE TABLE IF NOT EXISTS last_reports (
                user_id  uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                at       timestamptz NOT NULL DEFAULT now(),
                payload  jsonb NOT NULL
            )
            """,
        ),
    ),
]


def ensure_schema() -> None:
    """Apply any migration this database has not recorded yet."""
    global _SCHEMA_READY  # noqa: PLW0603 - per-instance memo
    if _SCHEMA_READY:
        return
    pool = _pool()          # outside the schema lock: it takes the pool lock itself
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        with pool.connection() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " id text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
            con.commit()
            done = {r[0] for r in con.execute("SELECT id FROM schema_migrations").fetchall()}
            for name, statements in MIGRATIONS:
                if name in done:
                    continue
                for sql in statements:
                    con.execute(sql)
                con.execute("INSERT INTO schema_migrations (id) VALUES (%s)"
                            " ON CONFLICT DO NOTHING", (name,))
                con.commit()
        _SCHEMA_READY = True


def sweep_expired() -> None:
    """Drop the short-lived rows. Cheap enough to run on any auth request."""
    with connection() as con:
        con.execute("DELETE FROM sessions WHERE expires_at < now()")
        con.execute("DELETE FROM login_tokens WHERE expires_at < now() - interval '1 day'")
        con.execute("DELETE FROM oauth_states WHERE expires_at < now()")
