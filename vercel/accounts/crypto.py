#!/usr/bin/env python3
"""Secrets handling: token hashing, and encryption for third-party tokens.

Two different jobs, deliberately kept apart:

* Session cookies and magic-link tokens are *hashed* (SHA-256). The database
  never holds a value that could be replayed, and there is nothing to decrypt.
* A Lichess access token has to be usable later, so it is *encrypted* with
  AES-256-GCM under a key that lives only in the environment. A database dump
  on its own does not hand anyone a working token.

`LEAKLAB_ENCRYPTION_KEY` is 32 bytes, base64url-encoded — generate one with
`python3 -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

KEY_ENV = "LEAKLAB_ENCRYPTION_KEY"
_AAD = b"leaklab:oauth-token:v1"


class SecretsNotConfigured(RuntimeError):
    """The deployment is missing a key it needs."""


def new_token(nbytes: int = 32) -> str:
    """A URL-safe random secret, for a cookie or a link."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """The stored form of a bearer secret."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def same_token(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")


def _key() -> bytes:
    raw = os.environ.get(KEY_ENV, "").strip()
    if not raw:
        raise SecretsNotConfigured(f"{KEY_ENV} is not set")
    try:
        key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except Exception as exc:  # noqa: BLE001
        raise SecretsNotConfigured(f"{KEY_ENV} is not valid base64") from exc
    if len(key) != 32:
        raise SecretsNotConfigured(f"{KEY_ENV} must decode to 32 bytes, got {len(key)}")
    return key


def _aesgcm():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: PLC0415

    return AESGCM


def encryption_available() -> bool:
    """True only if we could actually encrypt: a key *and* a working backend.

    Callers use this to decide whether to store a third-party token at all, so a
    key without a usable AES implementation has to read as "no".
    """
    try:
        _key()
        _aesgcm()
    # BaseException, not Exception: a cryptography build whose native bindings
    # do not load raises a pyo3 PanicException, which is not an Exception.
    except BaseException:  # noqa: BLE001, B036
        return False
    return True


def encrypt(plaintext: str) -> str:
    """AES-256-GCM, returned as base64url of nonce||ciphertext||tag."""
    if not plaintext:
        return ""
    AESGCM = _aesgcm()  # noqa: N806 - the library's own name

    nonce = os.urandom(12)
    blob = nonce + AESGCM(_key()).encrypt(nonce, plaintext.encode("utf-8"), _AAD)
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt(blob: str) -> str:
    """The inverse of `encrypt`. Returns '' if the value cannot be opened."""
    if not blob:
        return ""
    try:
        AESGCM = _aesgcm()  # noqa: N806 - the library's own name
        raw = base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4))
        return AESGCM(_key()).decrypt(raw[:12], raw[12:], _AAD).decode("utf-8")
    except BaseException:  # noqa: BLE001, B036 - a rotated key must not break sign-in
        return ""


# ---------------------------------------------------------------------- PKCE
def pkce_pair() -> tuple[str, str]:
    """A PKCE verifier and its S256 challenge.

    Lichess issues public clients no secret, so the verifier is the only thing
    binding the callback to the browser that started the flow.
    """
    verifier = base64.urlsafe_b64encode(os.urandom(48)).decode("ascii").rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge
