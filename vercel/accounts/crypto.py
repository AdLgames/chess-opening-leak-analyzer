#!/usr/bin/env python3
"""Secrets handling: PKCE, and the hashing of everything we keep.

Session cookies and magic-link tokens are *hashed* (SHA-256) before they are
stored, so the database never holds a value that could be replayed, and there is
nothing to decrypt.

There is deliberately no encryption here, because there is deliberately nothing
to encrypt. The Lichess access token is used once, during the callback, to ask
Lichess who just signed in — and then discarded. The scope requested is
`preference:read`, which grants no more than the public API already gives, so
keeping the token would be pure liability for a capability the app does not use.
The safest way to hold a credential is not to hold it.

That also keeps this module to the standard library, which matters more than it
sounds: the function ships a 79 MB engine and a 19 MB opening book alongside it,
so every megabyte of dependency is one the bundle cannot spend elsewhere.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

_TOKEN_BYTES = 32


def new_token(nbytes: int = _TOKEN_BYTES) -> str:
    """A URL-safe random secret, for a cookie or a link."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """The stored form of a bearer secret."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def same_token(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")


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
