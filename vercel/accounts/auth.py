#!/usr/bin/env python3
"""Sign-in, sessions, and the two account rights that are not optional.

Two ways in, chosen because of where the games come from:

* **Lichess OAuth (PKCE).** Lichess issues public clients no secret, so the
  whole flow is the authorisation code plus a verifier held server-side for the
  few minutes the browser is away. One tap for a Lichess player.
* **Email magic link.** Chess.com has no public OAuth at all, so its players
  get a single-use link instead. No passwords are stored anywhere in this app.

A session is a random token in an HttpOnly cookie; the database keeps only its
hash, which makes a sign-out an actual revocation rather than a client-side
forget.

`/api/auth/export` and `/api/auth/delete` are part of the first release on
purpose: once the analyser keeps a record of someone's play, taking it away
again has to be as easy as making it.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from . import crypto
from . import db

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE = "leaklab_session"
SESSION_DAYS = 45
LOGIN_TOKEN_MINUTES = 20
OAUTH_STATE_MINUTES = 15

LICHESS_AUTHORIZE = "https://lichess.org/oauth"
LICHESS_TOKEN = "https://lichess.org/api/token"
LICHESS_ACCOUNT = "https://lichess.org/api/account"
LICHESS_SCOPES = "preference:read"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")
SAFE_REDIRECT = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/?-]*$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ plumbing
def site_url(request: Request) -> str:
    """The public origin, so redirect URIs match what the browser actually used."""
    configured = os.environ.get("LEAKLAB_SITE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = request.headers.get("x-forwarded-proto") or "https"
    if not host:
        raise HTTPException(500, "Cannot work out this deployment's own URL")
    return f"{proto}://{host}"


def safe_redirect(value: str | None, fallback: str = "/app/") -> str:
    """Only ever bounce back to a path on this site — never to an absolute URL."""
    candidate = (value or "").strip()
    if candidate.startswith("//") or not SAFE_REDIRECT.match(candidate):
        return fallback
    return candidate


def set_session_cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=site_url(request).startswith("https://"),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def start_session(user_id: str, request: Request) -> str:
    token = crypto.new_token()
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at, user_agent)"
        " VALUES (%s, %s, %s, %s)",
        (crypto.hash_token(token), user_id, _now() + timedelta(days=SESSION_DAYS),
         (request.headers.get("user-agent") or "")[:300]),
    )
    return token


def current_user(request: Request) -> dict[str, Any] | None:
    """The signed-in user, or None. Never raises for an anonymous visitor."""
    token = request.cookies.get(COOKIE)
    if not token or not db.configured():
        return None
    try:
        row = db.query_one(
            "SELECT u.id, u.email, u.display_name, u.created_at"
            "  FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token_hash = %s AND s.expires_at > now()",
            (crypto.hash_token(token),))
    except db.DatabaseUnavailable:
        return None
    if row:
        db.execute("UPDATE users SET last_seen_at = now() WHERE id = %s", (row["id"],))
    return row


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Sign in to do that")
    return user


def _accounts(user_id: str) -> list[dict[str, Any]]:
    rows = db.query(
        "SELECT provider, username, linked_at FROM linked_accounts WHERE user_id = %s"
        " ORDER BY linked_at", (user_id,))
    return [{"provider": r["provider"], "username": r["username"],
             "linked_at": r["linked_at"].isoformat()} for r in rows]


def user_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["id"]),
        "email": user.get("email") or "",
        "name": user.get("display_name") or "",
        "created_at": user["created_at"].isoformat() if user.get("created_at") else "",
        "accounts": _accounts(user["id"]),
    }


def _find_or_create_by_email(email: str) -> dict[str, Any]:
    email = email.strip().lower()
    existing = db.query_one(
        "SELECT id, email, display_name, created_at FROM users WHERE email = %s", (email,))
    if existing:
        return existing
    uid = str(uuid.uuid4())
    db.execute("INSERT INTO users (id, email, display_name) VALUES (%s, %s, %s)"
               " ON CONFLICT (email) DO NOTHING", (uid, email, email.split("@")[0]))
    return db.query_one(
        "SELECT id, email, display_name, created_at FROM users WHERE email = %s", (email,))


# ----------------------------------------------------------------- endpoints
@router.get("/me")
def me(request: Request) -> dict[str, Any]:
    """Who is signed in, and what this deployment is able to offer."""
    ready = db.configured()
    user = current_user(request) if ready else None
    return {
        "signed_in": bool(user),
        "user": user_payload(user) if user else None,
        "methods": {
            "lichess": bool(os.environ.get("LICHESS_CLIENT_ID", "").strip()) and ready,
            "email": bool(os.environ.get("RESEND_API_KEY", "").strip() or _dev_links()) and ready,
        },
        "database": ready,
    }


@router.post("/logout")
def logout(request: Request) -> Response:
    token = request.cookies.get(COOKIE)
    if token and db.configured():
        try:
            db.execute("DELETE FROM sessions WHERE token_hash = %s", (crypto.hash_token(token),))
        except db.DatabaseUnavailable:
            pass
    response = JSONResponse({"signed_in": False})
    clear_session_cookie(response)
    return response


# ------------------------------------------------------------ lichess oauth
@router.get("/lichess/start")
def lichess_start(request: Request, redirect: str = "/app/") -> RedirectResponse:
    client_id = os.environ.get("LICHESS_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(503, "Lichess sign-in is not configured on this deployment")
    db.sweep_expired()
    verifier, challenge = crypto.pkce_pair()
    state = crypto.new_token(24)
    db.execute(
        "INSERT INTO oauth_states (state, verifier, redirect_to, expires_at)"
        " VALUES (%s, %s, %s, %s)",
        (state, verifier, safe_redirect(redirect),
         _now() + timedelta(minutes=OAUTH_STATE_MINUTES)))
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": f"{site_url(request)}/api/auth/lichess/callback",
        "scope": LICHESS_SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
    }
    return RedirectResponse(f"{LICHESS_AUTHORIZE}?{urllib.parse.urlencode(params)}", 302)


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read().decode("utf-8"))


@router.get("/lichess/callback")
def lichess_callback(request: Request, code: str = "", state: str = "",
                     error: str = "") -> Response:
    if error:
        return RedirectResponse(f"/app/?auth_error={urllib.parse.quote(error)}", 302)
    client_id = os.environ.get("LICHESS_CLIENT_ID", "").strip()
    if not client_id or not code or not state:
        raise HTTPException(400, "Incomplete authorisation response")

    pending = db.query_one(
        "DELETE FROM oauth_states WHERE state = %s AND expires_at > now()"
        " RETURNING verifier, redirect_to", (state,))
    if not pending:
        # Either a replay, a stale tab, or a request that never started here.
        raise HTTPException(400, "That sign-in link has expired — start again")

    try:
        token_response = _post_json(LICHESS_TOKEN, {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": pending["verifier"],
            "redirect_uri": f"{site_url(request)}/api/auth/lichess/callback",
            "client_id": client_id,
        })
        access_token = str(token_response.get("access_token") or "")
        if not access_token:
            raise HTTPException(502, "Lichess did not return an access token")
        account = _get_json(LICHESS_ACCOUNT, access_token)
    except urllib.error.URLError as exc:
        raise HTTPException(502, f"Lichess did not answer: {exc}") from exc

    provider_id = str(account.get("id") or "").lower()
    username = str(account.get("username") or provider_id)
    if not provider_id:
        raise HTTPException(502, "Lichess did not identify the account")

    # The token has now done its only job: it told us who signed in. It is not
    # stored — the scope asked for grants nothing the public API does not, so
    # keeping it would be a credential held for no capability.

    linked = db.query_one(
        "SELECT user_id FROM linked_accounts WHERE provider = 'lichess' AND provider_user_id = %s",
        (provider_id,))
    if linked:
        user_id = str(linked["user_id"])
        db.execute(
            "UPDATE linked_accounts SET username = %s, scopes = %s, linked_at = now()"
            " WHERE provider = 'lichess' AND provider_user_id = %s",
            (username, LICHESS_SCOPES, provider_id))
    else:
        signed_in = current_user(request)
        if signed_in:
            user_id = str(signed_in["id"])  # linking a second identity to one account
        else:
            user_id = str(uuid.uuid4())
            db.execute("INSERT INTO users (id, display_name) VALUES (%s, %s)",
                       (user_id, username))
        db.execute(
            "INSERT INTO linked_accounts (provider, provider_user_id, user_id, username, scopes)"
            " VALUES ('lichess', %s, %s, %s, %s)",
            (provider_id, user_id, username, LICHESS_SCOPES))

    token = start_session(user_id, request)
    response = RedirectResponse(safe_redirect(pending["redirect_to"]), 302)
    set_session_cookie(response, token, request)
    return response


# -------------------------------------------------------------- magic links
def _dev_links() -> bool:
    """Return sign-in links in the response instead of emailing them.

    For a preview deployment with no mail provider wired up. It hands anyone who
    can guess an address a way in, so it is refused on the production host.
    """
    return os.environ.get("LEAKLAB_DEV_MAGIC_LINKS", "").strip() == "1" and \
        os.environ.get("VERCEL_ENV", "development") != "production"


def _send_email(to: str, subject: str, text: str) -> bool:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("MAIL_FROM", "").strip() or "Opening Leak Lab <noreply@chessleaklab.co.uk>"
    if not key:
        return False
    body = json.dumps({"from": sender, "to": [to], "subject": subject, "text": text}).encode()
    req = urllib.request.Request("https://api.resend.com/emails", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15):  # noqa: S310 - fixed https host
            return True
    except urllib.error.URLError:
        return False


@router.post("/email/request")
async def email_request(request: Request) -> dict[str, Any]:
    payload = await request.json()
    email = str(payload.get("email") or "").strip().lower()
    redirect = safe_redirect(str(payload.get("redirect") or "/app/"))
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "That does not look like an email address")
    db.sweep_expired()

    # Rate limit per address, so this endpoint cannot be used to mail-bomb.
    recent = db.query_one(
        "SELECT count(*) AS n FROM login_tokens WHERE email = %s"
        " AND created_at > now() - interval '15 minutes'", (email,))
    if recent and int(recent["n"]) >= 5:
        raise HTTPException(429, "Too many sign-in links requested. Try again in a few minutes.")

    token = crypto.new_token()
    db.execute("INSERT INTO login_tokens (token_hash, email, expires_at) VALUES (%s, %s, %s)",
               (crypto.hash_token(token), email,
                _now() + timedelta(minutes=LOGIN_TOKEN_MINUTES)))
    link = (f"{site_url(request)}/api/auth/email/verify?token={urllib.parse.quote(token)}"
            f"&redirect={urllib.parse.quote(redirect)}")
    sent = _send_email(
        email,
        "Your Opening Leak Lab sign-in link",
        "Open this link to sign in and pick your leaks back up:\n\n"
        f"{link}\n\nIt works once and expires in {LOGIN_TOKEN_MINUTES} minutes. "
        "If you did not ask for it, ignore this email — nothing has been created.")
    # The same answer whether or not the address has an account here: knowing
    # which addresses are registered is not something a stranger should learn.
    out: dict[str, Any] = {"sent": True}
    if not sent:
        if not _dev_links():
            raise HTTPException(503, "Email sign-in is not configured on this deployment")
        out["link"] = link
        out["dev"] = True
    return out


@router.get("/email/verify")
def email_verify(request: Request, token: str = "", redirect: str = "/app/") -> Response:
    if not token:
        raise HTTPException(400, "No sign-in token")
    row = db.query_one(
        "UPDATE login_tokens SET used_at = now() WHERE token_hash = %s"
        " AND used_at IS NULL AND expires_at > now() RETURNING email",
        (crypto.hash_token(token),))
    if not row:
        return RedirectResponse("/app/?auth_error=expired", 302)
    user = _find_or_create_by_email(row["email"])
    session = start_session(str(user["id"]), request)
    response = RedirectResponse(safe_redirect(redirect), 302)
    set_session_cookie(response, session, request)
    return response


# -------------------------------------------------------- export and delete
@router.get("/export")
def export_account(request: Request) -> Response:
    """Everything this deployment holds about the signed-in user, as one file."""
    user = require_user(request)
    uid = user["id"]

    def rows(sql: str) -> list[dict[str, Any]]:
        return json.loads(json.dumps(db.query(sql, (uid,)), default=str))

    payload = {
        "exported_at": _now().isoformat(),
        "account": user_payload(user),
        "runs": rows("SELECT * FROM runs WHERE user_id = %s ORDER BY ran_at"),
        "leaks": rows("SELECT * FROM leaks WHERE user_id = %s ORDER BY last_seen_at"),
        "repertoire": rows("SELECT * FROM repertoire_commits WHERE user_id = %s"),
        "drill_schedule": rows("SELECT * FROM drill_schedule WHERE user_id = %s"),
        "drill_attempts": rows("SELECT * FROM drill_attempts WHERE user_id = %s ORDER BY at"),
        "prefs": rows("SELECT key, value FROM user_prefs WHERE user_id = %s"),
        # the standing record behind accumulated leaks, and the evidence for it
        "decisions": rows("SELECT * FROM decisions WHERE user_id = %s ORDER BY games DESC"),
        "decision_games": rows("SELECT leak_key, game_id FROM decision_games"
                               " WHERE user_id = %s ORDER BY leak_key"),
        "run_games": rows("SELECT run_id, game_id FROM run_games WHERE user_id = %s"
                          " ORDER BY run_id"),
    }
    return Response(
        json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="opening-leak-lab-export.json"'})


@router.post("/delete")
async def delete_account(request: Request) -> Response:
    """Erase the account. Every other table cascades from `users`."""
    user = require_user(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - an empty body is a missing confirmation
        body = {}
    if str(body.get("confirm") or "").strip().upper() != "DELETE":
        raise HTTPException(400, 'Send {"confirm": "DELETE"} to erase the account')
    db.execute("DELETE FROM users WHERE id = %s", (user["id"],))
    response = JSONResponse({"deleted": True})
    clear_session_cookie(response)
    return response
