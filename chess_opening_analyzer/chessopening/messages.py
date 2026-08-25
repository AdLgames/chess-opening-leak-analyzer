"""Failures, said twice: once for the person, once for whoever has to fix it.

The analyzer began as a command-line tool, where "Stockfish not found. Bundle a local copy
with `python tools/install_stockfish.py`, or install it system-wide (apt install stockfish
/ brew install stockfish), or pass --engine /path/to/stockfish, or set STOCKFISH_PATH" is
exactly the right thing to say. That sentence then went straight into the browser, where it
lands in front of somebody who wanted to know why their openings are leaking points and is
now being told about environment variables.

So the CLI keeps its message and the dashboard gets a translation: a headline, one sentence
about what still works, and the original text kept as `technical` behind a disclosure for
the person who does want the command. Nothing is hidden — it is just not the first thing.

Deliberately a small table rather than anything clever. Pattern-matching on error strings
is brittle, so the fallback is honest ("Something went wrong") rather than a wrong guess,
and every branch keeps the original text.
"""
from __future__ import annotations

from typing import Any


def _friendly(headline: str, detail: str, technical: str = "",
              fixable: bool = True) -> dict[str, Any]:
    return {"headline": headline, "detail": detail, "technical": technical, "fixable": fixable}


def explain_failure(error: str | BaseException) -> dict[str, Any]:
    """Turn a raw failure into something worth reading in a browser."""
    raw = str(error)
    low = raw.lower()

    if "stockfish not found" in low or "engine not found" in low:
        return _friendly(
            "No chess engine on this computer",
            "Everything based on your results still works — which openings cost you points, "
            "how you score against the database, all of the practice. What you lose is the "
            "engine's verdict on individual moves.",
            raw,
        )
    if "opening database not found" in low or "file is not a database" in low:
        return _friendly(
            "The opening database is missing",
            "This is the file your games get compared against, and nothing can be judged "
            "without it. It ships with the app but is stored separately because of its "
            "size, so it may not have downloaded with everything else.",
            raw,
        )
    if "no pgn" in low or "no games" in low or "found 0 games" in low:
        return _friendly(
            "No games to read",
            "The file was opened but nothing in it looked like a chess game. Exports from "
            "Lichess, Chess.com, SCID and ChessBase all work — a PGN saved from somewhere "
            "else may not be.",
            raw,
        )
    if "not found" in low and ("user" in low or "player" in low or "404" in low):
        return _friendly(
            "That username did not turn up",
            "Check the spelling, and check it is on the site you picked — a Lichess name "
            "will not be found on Chess.com.",
            raw,
        )
    if "429" in low or "rate limit" in low or "too many requests" in low:
        return _friendly(
            "The chess site asked us to slow down",
            "Lichess and Chess.com limit how fast games can be downloaded. Waiting a minute "
            "and trying again almost always works.",
            raw,
        )
    if "timed out" in low or "timeout" in low:
        return _friendly(
            "That took too long and stopped",
            "Usually a slow connection or a very large archive. Asking for fewer games is "
            "the quickest way through.",
            raw,
        )
    if "connection" in low or "network" in low or "urlopen" in low or "resolve" in low:
        return _friendly(
            "Could not reach the chess site",
            "The analysis itself runs on this computer, but downloading your games needs a "
            "connection. Uploading a PGN file works with no connection at all.",
            raw,
        )
    return _friendly(
        "Something went wrong",
        "The details below are what the program reported. If this keeps happening they are "
        "the useful thing to include in a bug report.",
        raw,
        fixable=False,
    )
