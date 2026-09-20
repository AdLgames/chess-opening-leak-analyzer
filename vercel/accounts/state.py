#!/usr/bin/env python3
"""The signed-in user's progress against their own leaks.

The browser has always kept this in `localStorage` under a stable key —
`leakKey` is the position EPD plus the move the player actually made — so the
server uses exactly the same key. That is what makes a user's existing local
data importable as-is, and what lets two runs months apart talk about the same
leak.

The one piece of real logic here is the leak lifecycle, applied when a run is
recorded:

    open ──▶ drilling ──▶ fixed ──▶ regressed ──▶ drilling ...

A leak is `open` when a run finds it, `drilling` once the user has committed a
reply or drilled it, `fixed` when a later run over fresh games no longer finds
it, and `regressed` when a run after that finds it again. Nothing is ever
deleted by a run: the point of an account is that the history survives.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from . import db
from .auth import require_user

router = APIRouter(prefix="/api/state", tags=["state"])

MAX_RUNS = 200
MAX_LEAKS_PER_RUN = 400
MAX_REPORT_BYTES = 4 * 1024 * 1024

ACTIVE = ("open", "drilling", "regressed")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


# --------------------------------------------------------------------- reads
def _repertoire(uid: str) -> list[dict[str, Any]]:
    rows = db.query(
        "SELECT leak_key, status, answer, line, entry, decided_at"
        "  FROM repertoire_commits WHERE user_id = %s", (uid,))
    out = []
    for r in rows:
        entry = dict(r["entry"] or {})
        entry.update({"key": r["leak_key"], "status": r["status"], "answer": r["answer"],
                      "line": r["line"] or [],
                      "decidedAt": int(r["decided_at"].timestamp() * 1000)})
        out.append(entry)
    return out


def _runs(uid: str) -> list[dict[str, Any]]:
    rows = db.query(
        "SELECT id, ran_at, player, source, games, leaks, cost, summary"
        "  FROM runs WHERE user_id = %s ORDER BY ran_at", (uid,))
    return [{"id": r["id"], "at": int(r["ran_at"].timestamp() * 1000), "player": r["player"],
             "source": r["source"], "games": r["games"], "leaks": r["leaks"],
             "cost": r["cost"], **(r["summary"] or {})} for r in rows]


def _drills(uid: str) -> dict[str, Any]:
    rows = db.query(
        "SELECT leak_key, label, right_n, wrong_n, streak, last_at, due_at"
        "  FROM drill_schedule WHERE user_id = %s", (uid,))
    return {r["leak_key"]: {
        "key": r["leak_key"], "label": r["label"], "right": r["right_n"], "wrong": r["wrong_n"],
        "streak": r["streak"],
        "last": int(r["last_at"].timestamp() * 1000) if r["last_at"] else 0,
        "due": int(r["due_at"].timestamp() * 1000) if r["due_at"] else 0,
    } for r in rows}


def _prefs(uid: str) -> dict[str, Any]:
    return {r["key"]: r["value"] for r in
            db.query("SELECT key, value FROM user_prefs WHERE user_id = %s", (uid,))}


@router.get("")
def read_state(request: Request) -> dict[str, Any]:
    """Everything the app needs to open on a device that has never seen this user."""
    user = require_user(request)
    uid = user["id"]
    report = db.query_one("SELECT at, payload FROM last_reports WHERE user_id = %s", (uid,))
    return {
        "repertoire": _repertoire(uid),
        "runs": _runs(uid),
        "drills": _drills(uid),
        "prefs": _prefs(uid),
        "report": (report or {}).get("payload"),
        "report_at": _iso((report or {}).get("at")),
        "progress": progress(request),
    }


@router.get("/progress")
def progress(request: Request) -> dict[str, Any]:
    """Where the user stands: what is open, what is fixed, and what came back."""
    user = require_user(request)
    uid = user["id"]
    counts = {r["status"]: int(r["n"]) for r in db.query(
        "SELECT status, count(*) AS n FROM leaks WHERE user_id = %s GROUP BY status", (uid,))}
    shed = db.query_one(
        "SELECT coalesce(sum(first_cost), 0) AS total,"
        "       coalesce(sum(first_cost) FILTER (WHERE status = 'fixed'), 0) AS fixed"
        "  FROM leaks WHERE user_id = %s", (uid,))
    recent = db.query(
        "SELECT leak_key, opening, played, move_number, status, cost, first_cost, last_seen_at"
        "  FROM leaks WHERE user_id = %s ORDER BY last_seen_at DESC, cost DESC LIMIT 50", (uid,))
    return {
        "counts": {k: counts.get(k, 0) for k in ("open", "drilling", "fixed", "regressed")},
        "cost_found": round(_num((shed or {}).get("total")), 2),
        "cost_closed": round(_num((shed or {}).get("fixed")), 2),
        "runs": len(_runs(uid)),
        "leaks": [{"key": r["leak_key"], "opening": r["opening"], "played": r["played"],
                   "moveNumber": r["move_number"], "status": r["status"], "cost": r["cost"],
                   "firstCost": r["first_cost"], "lastSeen": _iso(r["last_seen_at"])}
                  for r in recent],
    }


# -------------------------------------------------------------------- writes
def _upsert_repertoire(uid: str, entry: dict[str, Any]) -> None:
    key = str(entry.get("key") or "")
    if not key:
        raise HTTPException(400, "A repertoire entry needs a key")
    slim = {k: v for k, v in entry.items()
            if k in ("position", "fen", "color", "eco", "opening", "played", "moveNumber",
                     "games", "cost", "flag")}
    db.execute(
        "INSERT INTO repertoire_commits (user_id, leak_key, status, answer, line, entry)"
        " VALUES (%s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (user_id, leak_key) DO UPDATE SET status = EXCLUDED.status,"
        "   answer = EXCLUDED.answer, line = EXCLUDED.line, entry = EXCLUDED.entry,"
        "   decided_at = now()",
        (uid, key, str(entry.get("status") or "committed"), str(entry.get("answer") or ""),
         json.dumps(entry.get("line") or []), json.dumps(slim)))
    # Committing a reply is the moment a leak stops being merely known about.
    if entry.get("status") == "committed":
        db.execute("UPDATE leaks SET status = 'drilling'"
                   " WHERE user_id = %s AND leak_key = %s AND status IN ('open', 'regressed')",
                   (uid, key))


@router.post("/repertoire")
async def put_repertoire(request: Request) -> dict[str, Any]:
    user = require_user(request)
    body = await request.json()
    entries = body.get("entries") or ([body["entry"]] if body.get("entry") else [])
    for entry in entries[:MAX_LEAKS_PER_RUN]:
        _upsert_repertoire(str(user["id"]), entry)
    return {"ok": True, "repertoire": _repertoire(user["id"])}


@router.post("/repertoire/remove")
async def drop_repertoire(request: Request) -> dict[str, Any]:
    user = require_user(request)
    key = str((await request.json()).get("key") or "")
    db.execute("DELETE FROM repertoire_commits WHERE user_id = %s AND leak_key = %s",
               (user["id"], key))
    return {"ok": True}


@router.post("/drill")
async def put_drill(request: Request) -> dict[str, Any]:
    """Log one attempt and move the review schedule on."""
    user = require_user(request)
    uid = str(user["id"])
    body = await request.json()
    key = str(body.get("key") or "")
    if not key:
        raise HTTPException(400, "A drill attempt needs a leak key")
    correct = bool(body.get("correct"))
    db.execute("INSERT INTO drill_attempts (user_id, leak_key, correct, played)"
               " VALUES (%s, %s, %s, %s)", (uid, key, correct, str(body.get("played") or "")))
    # Same spacing ladder the browser has always used: 1, 3, 7, 16, 35 days on a
    # streak, and half a day after a miss.
    db.execute(
        """
        INSERT INTO drill_schedule (user_id, leak_key, label, right_n, wrong_n, streak,
                                    last_at, due_at)
        VALUES (%s, %s, %s, %s, %s, %s, now(),
                now() + (CASE WHEN %s THEN interval '3 days' ELSE interval '12 hours' END))
        ON CONFLICT (user_id, leak_key) DO UPDATE SET
            label   = CASE WHEN EXCLUDED.label <> '' THEN EXCLUDED.label
                           ELSE drill_schedule.label END,
            right_n = drill_schedule.right_n + EXCLUDED.right_n,
            wrong_n = drill_schedule.wrong_n + EXCLUDED.wrong_n,
            streak  = CASE WHEN %s THEN drill_schedule.streak + 1 ELSE 0 END,
            last_at = now(),
            due_at  = now() + CASE WHEN %s THEN
                          (ARRAY[interval '1 day', interval '3 days', interval '7 days',
                                 interval '16 days', interval '35 days'])
                          [least(drill_schedule.streak + 1, 4) + 1]
                      ELSE interval '12 hours' END
        """,
        (uid, key, str(body.get("label") or ""), 1 if correct else 0, 0 if correct else 1,
         1 if correct else 0, correct, correct, correct))
    db.execute("UPDATE leaks SET status = 'drilling'"
               " WHERE user_id = %s AND leak_key = %s AND status IN ('open', 'regressed')",
               (uid, key))
    return {"ok": True, "drills": _drills(uid)}


@router.post("/pref")
async def put_pref(request: Request) -> dict[str, Any]:
    user = require_user(request)
    body = await request.json()
    key = str(body.get("key") or "")
    if not key:
        raise HTTPException(400, "A preference needs a key")
    db.execute("INSERT INTO user_prefs (user_id, key, value) VALUES (%s, %s, %s)"
               " ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value",
               (user["id"], key, json.dumps(body.get("value"))))
    return {"ok": True}


def _record_run(uid: str, run: dict[str, Any], leaks: list[dict[str, Any]]) -> None:
    run_id = str(run.get("id") or "")
    if not run_id:
        raise HTTPException(400, "A run needs an id")
    summary = {k: v for k, v in run.items()
               if k not in ("id", "at", "player", "source", "games", "leaks", "cost")}
    db.execute(
        "INSERT INTO runs (id, user_id, ran_at, player, source, games, leaks, cost, summary)"
        " VALUES (%s, %s, coalesce(to_timestamp(%s), now()), %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (user_id, id) DO UPDATE SET summary = EXCLUDED.summary,"
        "   games = EXCLUDED.games, leaks = EXCLUDED.leaks, cost = EXCLUDED.cost",
        (run_id, uid, (_num(run.get("at")) / 1000.0) or None, str(run.get("player") or ""),
         str(run.get("source") or ""), int(_num(run.get("games"))), int(_num(run.get("leaks"))),
         _num(run.get("cost")), json.dumps(summary)))

    seen: list[str] = []
    for row in leaks[:MAX_LEAKS_PER_RUN]:
        key = str(row.get("key") or "")
        if not key:
            continue
        seen.append(key)
        db.execute(
            "INSERT INTO leaks (user_id, leak_key, position, fen, color, eco, opening, played,"
            "                   move_number, status, cost, first_cost, games, flag)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'open', %s, %s, %s, %s)"
            " ON CONFLICT (user_id, leak_key) DO UPDATE SET"
            "   cost = EXCLUDED.cost, games = EXCLUDED.games, flag = EXCLUDED.flag,"
            "   opening = EXCLUDED.opening, last_seen_at = now(),"
            # a leak the user had closed and this run found again has regressed;
            # otherwise whatever progress it was already making is left alone
            "   status = CASE WHEN leaks.status = 'fixed' THEN 'regressed'"
            "                 ELSE leaks.status END",
            (uid, key, str(row.get("position") or ""), str(row.get("fen") or ""),
             str(row.get("color") or ""), str(row.get("eco") or ""),
             str(row.get("opening") or ""), str(row.get("played") or ""),
             int(_num(row.get("moveNumber"))), _num(row.get("cost")), _num(row.get("cost")),
             int(_num(row.get("games"))), str(row.get("flag") or "")))

    # Anything the user was working on that this run no longer finds is fixed.
    if seen:
        db.execute(
            "UPDATE leaks SET status = 'fixed', last_seen_at = now()"
            " WHERE user_id = %s AND status IN ('open', 'drilling', 'regressed')"
            "   AND NOT (leak_key = ANY(%s))", (uid, seen))
    db.execute(
        "DELETE FROM runs WHERE user_id = %s AND id NOT IN ("
        "  SELECT id FROM runs WHERE user_id = %s ORDER BY ran_at DESC LIMIT %s)",
        (uid, uid, MAX_RUNS))


@router.post("/run")
async def put_run(request: Request) -> dict[str, Any]:
    """Record a finished run and move every leak's lifecycle on."""
    user = require_user(request)
    uid = str(user["id"])
    body = await request.json()
    run = body.get("run") or {}
    _record_run(uid, run, list(body.get("leaks") or []))
    report = body.get("report")
    if report is not None:
        blob = json.dumps(report)
        if len(blob.encode("utf-8")) <= MAX_REPORT_BYTES:
            db.execute("INSERT INTO last_reports (user_id, payload) VALUES (%s, %s)"
                       " ON CONFLICT (user_id) DO UPDATE SET payload = EXCLUDED.payload,"
                       " at = now()", (uid, blob))
    return {"ok": True, "progress": progress(request)}


@router.post("/import")
async def import_local(request: Request) -> dict[str, Any]:
    """Adopt whatever the browser was already keeping, once, at first sign-in.

    Users have been using this app without an account, so their repertoire and
    drill history exist locally. Signing in must not look like starting over.
    """
    user = require_user(request)
    uid = str(user["id"])
    body = await request.json()

    for entry in list(body.get("repertoire") or [])[:MAX_LEAKS_PER_RUN]:
        if entry.get("key"):
            _upsert_repertoire(uid, entry)
    for run in list(body.get("runs") or [])[-MAX_RUNS:]:
        if run.get("id"):
            _record_run(uid, run, [])
    for key, d in (body.get("drills") or {}).items():
        db.execute(
            "INSERT INTO drill_schedule (user_id, leak_key, label, right_n, wrong_n, streak,"
            "                            last_at, due_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s), to_timestamp(%s))"
            " ON CONFLICT (user_id, leak_key) DO UPDATE SET"
            # take the better of the two histories rather than clobbering either
            "   right_n = greatest(drill_schedule.right_n, EXCLUDED.right_n),"
            "   wrong_n = greatest(drill_schedule.wrong_n, EXCLUDED.wrong_n),"
            "   streak  = greatest(drill_schedule.streak, EXCLUDED.streak),"
            "   due_at  = least(drill_schedule.due_at, EXCLUDED.due_at)",
            (uid, key, str(d.get("label") or ""), int(_num(d.get("right"))),
             int(_num(d.get("wrong"))), int(_num(d.get("streak"))),
             _num(d.get("last")) / 1000.0 or None, _num(d.get("due")) / 1000.0 or None))
    for key, value in (body.get("prefs") or {}).items():
        db.execute("INSERT INTO user_prefs (user_id, key, value) VALUES (%s, %s, %s)"
                   " ON CONFLICT (user_id, key) DO NOTHING", (uid, key, json.dumps(value)))
    return read_state(request)
