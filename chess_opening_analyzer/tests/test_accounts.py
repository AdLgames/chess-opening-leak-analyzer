"""Accounts: the two promises that are hard to walk back once people sign up.

The hosted deployment's account code lives in `vercel/accounts/`, which needs
neither python-chess nor the engine. FastAPI is not installed everywhere, so the
modules under test are loaded by path rather than imported as a package — these
two are pure and import nothing from the web layer.

What is checked here is what would be expensive to get wrong:

* PKCE is actually PKCE. A wrong challenge means Lichess rejects every callback.
* A Lichess token is not recoverable from the database alone.
* `DELETE FROM users` really does erase everything, because that is the promise
  the account-deletion button makes.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACCOUNTS = os.path.join(ROOT, "vercel", "accounts")


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"_acct_{name}",
                                                  os.path.join(ACCOUNTS, f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


crypto = load("crypto")
db = load("db")


# --------------------------------------------------------------------- crypto
def test_pkce_challenge_is_s256_of_the_verifier():
    verifier, challenge = crypto.pkce_pair()
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    assert challenge == expected
    # Both halves must survive a URL without escaping, and neither may be padded.
    assert re.fullmatch(r"[A-Za-z0-9_-]+", verifier)
    assert re.fullmatch(r"[A-Za-z0-9_-]+", challenge)
    assert crypto.pkce_pair()[0] != verifier          # a fresh one every flow


def test_tokens_are_stored_only_as_hashes():
    token = crypto.new_token()
    stored = crypto.hash_token(token)
    assert stored != token
    assert len(stored) == 64 and crypto.hash_token(token) == stored
    assert crypto.same_token(stored, crypto.hash_token(token))
    assert not crypto.same_token(stored, crypto.hash_token(crypto.new_token()))


def test_oauth_tokens_round_trip_and_are_opaque_without_the_key():
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    os.environ[crypto.KEY_ENV] = key
    try:
        if not crypto.encryption_available():
            # No working AES backend on this machine. `encryption_available()`
            # saying so is itself the behaviour that matters: auth.py then
            # declines to store a token rather than storing it in the clear.
            return

        blob = crypto.encrypt("lip_secret_value")
        assert "lip_secret_value" not in blob
        assert crypto.decrypt(blob) == "lip_secret_value"
        assert crypto.encrypt("lip_secret_value") != blob   # a fresh nonce each time

        # A leaked database without the key yields nothing, and a rotated key
        # must fail closed rather than raising into a sign-in request.
        os.environ[crypto.KEY_ENV] = base64.urlsafe_b64encode(os.urandom(32)).decode()
        assert crypto.decrypt(blob) == ""
    finally:
        os.environ.pop(crypto.KEY_ENV, None)


def test_a_missing_or_malformed_key_is_reported_not_guessed():
    os.environ.pop(crypto.KEY_ENV, None)
    assert not crypto.encryption_available()
    for bad in ("not-base64!!", base64.urlsafe_b64encode(b"too short").decode()):
        os.environ[crypto.KEY_ENV] = bad
        assert not crypto.encryption_available()
    os.environ.pop(crypto.KEY_ENV, None)


def test_a_token_is_never_stored_unencrypted():
    # The callback writes `crypto.encrypt(...) if encryption_available() else None`.
    source = open(os.path.join(ACCOUNTS, "auth.py"), encoding="utf-8").read()
    assert "crypto.encrypt(access_token) if crypto.encryption_available() else None" in source
    assert "access_token_enc" in source and "access_token_enc=access_token" not in source


# --------------------------------------------------------------------- schema
USER_TABLES = ("linked_accounts", "sessions", "runs", "leaks", "repertoire_commits",
               "drill_schedule", "drill_attempts", "user_prefs", "last_reports")


def statements() -> list[str]:
    return [sql for _name, group in db.MIGRATIONS for sql in group]


def test_migration_ids_are_unique_and_ordered():
    ids = [name for name, _ in db.MIGRATIONS]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_every_statement_is_safe_to_run_twice():
    # Two cold starts can race each other, so replaying a migration must be a
    # no-op rather than an error.
    for sql in statements():
        assert "IF NOT EXISTS" in sql.upper(), sql.strip()[:80]


def test_deleting_a_user_erases_everything_that_hangs_off_them():
    sql = "\n".join(statements())
    for table in USER_TABLES:
        block = sql.split(f"CREATE TABLE IF NOT EXISTS {table}", 1)
        assert len(block) == 2, f"{table} is not created by any migration"
        body = block[1].split('"""', 1)[0]
        assert "REFERENCES users(id) ON DELETE CASCADE" in body, \
            f"{table} would survive an account deletion"


def test_progress_is_keyed_on_the_leak_key_the_browser_already_uses():
    sql = "\n".join(statements())
    for table in ("leaks", "repertoire_commits", "drill_schedule"):
        body = sql.split(f"CREATE TABLE IF NOT EXISTS {table}", 1)[1].split('"""', 1)[0]
        assert "leak_key" in body
        assert "PRIMARY KEY (user_id, leak_key)" in body, \
            f"{table} must hold exactly one row per user and leak"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
