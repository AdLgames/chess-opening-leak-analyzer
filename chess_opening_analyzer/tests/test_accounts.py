"""Accounts: the two promises that are hard to walk back once people sign up.

The hosted deployment's account code lives in `vercel/accounts/`, which needs
neither python-chess nor the engine. FastAPI is not installed everywhere, so the
modules under test are loaded by path rather than imported as a package — these
two are pure and import nothing from the web layer.

What is checked here is what would be expensive to get wrong:

* PKCE is actually PKCE. A wrong challenge means Lichess rejects every callback.
* A Lichess token is never written down in the first place.
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


def test_the_lichess_token_is_never_written_anywhere():
    """The safest way to hold a credential is not to hold it.

    The token is used once in the callback to ask Lichess who just signed in.
    If it ever reached a column, this would stop being true and someone would
    have to justify it again -- so the schema is asserted to have nowhere to
    put it, and the callback to hand it to no write.
    """
    auth_src = open(os.path.join(ACCOUNTS, "auth.py"), encoding="utf-8").read()
    assert "access_token" not in "\n".join(statements())
    for line in auth_src.splitlines():
        if "access_token" in line and ("INSERT" in line or "UPDATE" in line):
            raise AssertionError(f"the token reaches a write: {line.strip()}")


def test_the_account_code_needs_no_crypto_library():
    # The function already ships a 79 MB engine and a 19 MB book, so a
    # dependency has to earn its place. With no token to encrypt, this one
    # stopped earning it.
    source = open(os.path.join(ACCOUNTS, "crypto.py"), encoding="utf-8").read()
    requirements = open(os.path.join(ROOT, "vercel", "requirements.txt"),
                        encoding="utf-8").read()
    assert "cryptography" not in source
    assert "cryptography" not in requirements



# --------------------------------------------------------------------- schema
USER_TABLES = ("linked_accounts", "sessions", "runs", "leaks", "repertoire_commits",
               "drill_schedule", "drill_attempts", "user_prefs", "last_reports",
               "decisions", "decision_games", "run_games")


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
