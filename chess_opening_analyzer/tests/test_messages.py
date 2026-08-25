"""Failures, said in a way a chess player can act on."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chessopening.messages import explain_failure  # noqa: E402

ENGINE_ERROR = (
    "Stockfish not found. Bundle a local copy with `python tools/install_stockfish.py`, "
    "or install it system-wide (apt install stockfish / brew install stockfish), "
    "or pass --engine /path/to/stockfish, or set STOCKFISH_PATH."
)


def test_no_shell_commands_reach_the_headline_or_the_detail():
    """The command line message is right for the command line. In a browser it lands in
    front of somebody who wanted to know why their openings leak points."""
    out = explain_failure(ENGINE_ERROR)
    readable = f"{out['headline']} {out['detail']}"
    for token in ("apt install", "brew install", "python tools/", "STOCKFISH_PATH", "--engine"):
        assert token not in readable


def test_the_original_text_is_kept_rather_than_thrown_away():
    """Somebody does want the command; it just should not be the first thing."""
    assert explain_failure(ENGINE_ERROR)["technical"] == ENGINE_ERROR


def test_a_missing_engine_says_what_still_works():
    out = explain_failure(ENGINE_ERROR)
    assert "engine" in out["headline"].lower()
    assert "still works" in out["detail"]


def test_a_missing_book_says_that_nothing_can_be_judged_without_it():
    """Unlike the engine, this one is not a partial loss."""
    out = explain_failure("Local opening database not found at /x/openings.sqlite")
    assert "database" in out["headline"].lower()
    assert "nothing can be judged" in out["detail"]


def test_an_unbuilt_book_reads_as_the_same_problem():
    """A Git LFS pointer opens as a file and fails as a database — same fix, so the same
    message, rather than a raw sqlite3 error."""
    assert explain_failure("file is not a database")["headline"] == \
        explain_failure("Local opening database not found at /x")["headline"]


def test_a_wrong_username_suggests_the_thing_that_is_usually_wrong():
    out = explain_failure("Player not found: 404")
    assert "username" in out["headline"].lower()
    assert "Lichess" in out["detail"] and "Chess.com" in out["detail"]


def test_being_rate_limited_is_not_presented_as_the_users_mistake():
    out = explain_failure("HTTP Error 429: Too Many Requests")
    assert "slow down" in out["headline"]
    assert "trying again" in out["detail"]


def test_a_network_failure_points_at_the_path_that_needs_no_network():
    out = explain_failure("<urlopen error [Errno -3] Temporary failure in name resolution>")
    assert "no connection at all" in out["detail"]


def test_an_unrecognised_failure_does_not_guess():
    """A confidently wrong explanation is worse than admitting we do not know."""
    out = explain_failure("Segmentation fault (core dumped)")
    assert out["headline"] == "Something went wrong"
    assert out["fixable"] is False
    assert out["technical"] == "Segmentation fault (core dumped)"


def test_an_exception_works_as_well_as_a_string():
    out = explain_failure(FileNotFoundError(ENGINE_ERROR))
    assert "engine" in out["headline"].lower()


def test_every_branch_keeps_the_original_text():
    for raw in (ENGINE_ERROR, "opening database not found", "no games found",
                "HTTP Error 429", "connection refused", "read timed out", "who knows"):
        assert explain_failure(raw)["technical"] == raw
