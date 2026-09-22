#!/usr/bin/env python3
"""Postgres access for the hosted deployment.

The analyser itself is still stateless — this module exists only so a signed-in
user's progress against their leaks survives the run that found them.

The driver is pg8000: a pure-Python implementation of the Postgres wire
protocol. That is not a stylistic preference. This function already ships a
79 MB engine and a 19 MB opening book, and psycopg's binary distribution --
12 MB of vendored shared libraries -- is what the deployment refused to build;
pg8000 is 2.8 MB with no compiled object in it, and speaks the same protocol to
the same server, so nothing about the SQL below changes.

Connection handling is shaped by the serverless runtime. A function instance is
thrown away without warning, so there is no client-side pool: each request opens
a connection, runs inside one transaction, and closes it. That sounds wasteful
and is not — `POSTGRES_URL` from Vercel Postgres (Neon) already points at a
pooling endpoint, so the pooling happens on the far side, where it survives the
instance. Holding a second pool in front of it would only add a dependency and a
set of connections that die with the instance anyway.

The schema is applied by `ensure_schema()` on first use of an instance. Every
statement is `IF NOT EXISTS`, and `schema_migrations` records what has run, so
concurrent cold starts racing each other is harmless.
"""
from __future__ import annotations

import os
import threading
import urllib.parse
from contextlib import contextmanager
from typing import Any, Iterator

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False

# How long to wait for the database before giving up on a request. Short: the
# whole function has 60 seconds and the analysis needs nearly all of them.
CONNECT_TIMEOUT_S = 8


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
        import pg8000.dbapi  # noqa: F401, PLC0415
    except Exception:  # noqa: BLE001 - any failure here means "no database"
        return False
    return True


def configured() -> bool:
    return database_url() is not None and driver_available()


def _dsn(url: str) -> dict[str, Any]:
    """Split a Postgres URL into the keyword arguments pg8000 wants.

    pg8000 takes no URL, so this does what libpq would have done. `sslmode` is
    not one of its arguments either: a managed Postgres is TLS-only, so unless
    the URL explicitly disables it the connection is made over SSL.
    """
    parts = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parts.query)
    sslmode = (query.get("sslmode") or ["require"])[0]
    kwargs: dict[str, Any] = {
        "user": urllib.parse.unquote(parts.username or ""),
        "host": parts.hostname or "localhost",
        "port": parts.port or 5432,
        "database": urllib.parse.unquote((parts.path or "/").lstrip("/")) or None,
        "timeout": CONNECT_TIMEOUT_S,
    }
    if parts.password:
        kwargs["password"] = urllib.parse.unquote(parts.password)
    if sslmode not in ("disable", "allow"):
        import ssl  # noqa: PLC0415

        kwargs["ssl_context"] = ssl.create_default_context()
        if sslmode in ("require", "prefer"):
            # What libpq's `require` means: encrypt, but do not also demand that
            # the server's certificate chain to a CA this runtime happens to
            # trust. `verify-full` in the URL asks for the stricter thing.
            kwargs["ssl_context"].check_hostname = False
            kwargs["ssl_context"].verify_mode = ssl.CERT_NONE
    return kwargs


def _connect() -> Any:
    """One connection. The caller owns closing it."""
    url = database_url()
    if not url:
        raise DatabaseUnavailable(
            "No POSTGRES_URL is set. Accounts need a database — see vercel/README.md.")
    try:
        import pg8000.dbapi  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - deployment error
        raise DatabaseUnavailable(f"pg8000 is not installed: {exc}") from exc
    con = pg8000.dbapi.connect(**_dsn(url))
    con.autocommit = False
    return con


@contextmanager
def connection() -> Iterator[Any]:
    """A connection with the schema in place, committed on clean exit.

    Committing here rather than relying on the driver's context manager keeps
    the contract explicit: leave normally and the work is kept, raise and it is
    rolled back.
    """
    ensure_schema()
    con = _connect()
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def _rows(cur: Any) -> list[dict[str, Any]]:
    """Cursor rows as dicts, since every caller is building JSON."""
    if cur.description is None:
        return []
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


@contextmanager
def cursor() -> Iterator[Any]:
    with connection() as con:
        cur = con.cursor()
        try:
            yield cur
        finally:
            cur.close()


def query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(sql, params or ())
        return _rows(cur)


def query_one(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple | None = None) -> None:
    with cursor() as cur:
        cur.execute(sql, params or ())


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
    (
        "0003_accumulation",
        (
            # One row per decision the user has ever been seen to make, whether
            # or not any single run saw it often enough to judge. This is what
            # lets a line met twice a month become a leak after three months
            # instead of never.
            """
            CREATE TABLE IF NOT EXISTS decisions (
                user_id        uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                leak_key       text NOT NULL,
                position       text NOT NULL DEFAULT '',
                fen            text NOT NULL DEFAULT '',
                color          text NOT NULL DEFAULT '',
                eco            text NOT NULL DEFAULT '',
                opening        text NOT NULL DEFAULT '',
                line           text NOT NULL DEFAULT '',
                played         text NOT NULL DEFAULT '',
                move_number    integer NOT NULL DEFAULT 0,
                games          integer NOT NULL DEFAULT 0,
                score_sum      double precision NOT NULL DEFAULT 0,
                book_score_pct double precision,
                in_book        boolean NOT NULL DEFAULT false,
                promoted       boolean NOT NULL DEFAULT false,
                first_seen_at  timestamptz NOT NULL DEFAULT now(),
                last_seen_at   timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, leak_key)
            )
            """,
            "CREATE INDEX IF NOT EXISTS decisions_user_games ON decisions (user_id, games)",
            # The evidence itself: one row per (decision, game). The primary key
            # is the whole point — re-analysing an overlapping window inserts
            # nothing, so "your last 120 games" run monthly cannot inflate a
            # count by re-reading the same games.
            """
            CREATE TABLE IF NOT EXISTS decision_games (
                user_id   uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                leak_key  text NOT NULL,
                game_id   text NOT NULL,
                PRIMARY KEY (user_id, leak_key, game_id)
            )
            """,
            # Which games a run read at all, so a run can be recorded once and
            # recognised later.
            """
            CREATE TABLE IF NOT EXISTS run_games (
                user_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                run_id   text NOT NULL,
                game_id  text NOT NULL,
                PRIMARY KEY (user_id, run_id, game_id)
            )
            """,
            # Where a leak came from: one run finding it, or evidence adding up
            # across several. A promoted leak has no engine verdict behind it,
            # and the interface should be able to say so.
            "ALTER TABLE leaks ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'run'",
            "ALTER TABLE leaks ADD COLUMN IF NOT EXISTS runs_seen integer NOT NULL DEFAULT 1",
        ),
    ),
]


def ensure_schema() -> None:
    """Apply any migration this database has not recorded yet."""
    global _SCHEMA_READY  # noqa: PLW0603 - per-instance memo
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        con = _connect()
        try:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " id text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
            con.commit()
            cur.execute("SELECT id FROM schema_migrations")
            done = {row[0] for row in cur.fetchall()}
            for name, statements in MIGRATIONS:
                if name in done:
                    continue
                # One migration per transaction: a half-applied one must not be
                # recorded, and a concurrent cold start may be doing the same.
                for sql in statements:
                    cur.execute(sql)
                cur.execute("INSERT INTO schema_migrations (id) VALUES (%s)"
                            " ON CONFLICT DO NOTHING", (name,))
                con.commit()
            cur.close()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()
        _SCHEMA_READY = True


def sweep_expired() -> None:
    """Drop the short-lived rows. Cheap enough to run on any auth request."""
    with cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE expires_at < now()")
        cur.execute("DELETE FROM login_tokens WHERE expires_at < now() - interval '1 day'")
        cur.execute("DELETE FROM oauth_states WHERE expires_at < now()")


def diagnosis() -> dict[str, Any]:
    """Why accounts are off, in terms safe to serve publicly.

    `configured()` collapses two very different failures into one False, which
    is unhelpful when the only view of the deployment is a phone browser. This
    separates them, and reports names and exception classes only — never the
    connection string, the host, or a driver message, any of which would put
    infrastructure detail on a public endpoint.
    """
    found = next((n for n in ("POSTGRES_PRISMA_URL", "POSTGRES_URL", "DATABASE_URL")
                  if os.environ.get(n, "").strip()), None)
    out: dict[str, Any] = {"url_env": found, "driver": driver_available()}
    if not found or not out["driver"]:
        out["connect"] = "not attempted"
        return out
    try:
        conn = _connect()
    except Exception as exc:  # noqa: BLE001 - any failure is a finding here
        # The SQLSTATE is worth reporting and safe to: it separates a refused
        # password (28P01) from a missing database (3D000) in five standard
        # characters. The message itself is not — pg8000 spells out the host
        # and port it tried, which is not for a public endpoint.
        out["connect"] = type(exc).__name__
        args = exc.args[0] if exc.args else None
        if isinstance(args, dict) and args.get("C"):
            out["sqlstate"] = str(args["C"])
    else:
        try:
            conn.close()
        except Exception:  # noqa: BLE001, S110 - already past the useful answer
            pass
        out["connect"] = "ok"
    return out
