"""The hosted function's time budget.

`api/index.py` is only importable once `prepare.py` has assembled the bundle
beside it, so this skips in a bare checkout the same way the database tests do.
Where the bundle exists — a deployment, or a local build — the arithmetic that
keeps a run inside the function's limit is worth pinning: get it wrong and the
request is killed and returns nothing at all, which is the one outcome the
graceful degradation exists to avoid.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERCEL = os.path.join(ROOT, "vercel")


def _load():
    path = os.path.join(VERCEL, "api", "index.py")
    if not os.path.isfile(path) or not os.path.isdir(os.path.join(VERCEL, "chessopening")):
        return None
    if VERCEL not in sys.path:
        sys.path.append(VERCEL)
    try:
        spec = importlib.util.spec_from_file_location("_hosted_index", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001 - a missing dependency is "cannot run here"
        return None
    return module


index = _load()
pytestmark = pytest.mark.skipif(index is None,
                                reason="the deployable bundle is not assembled here")


def test_a_fresh_request_gets_the_whole_engine_budget():
    assert index.engine_budget_for(0.0) == float(index.LIMITS["time_budget_s"])


def test_time_already_spent_comes_out_of_the_engine_pass():
    """Fetching a bigger archive shortens the engine pass rather than overrunning."""
    spent = 20.0
    got = index.engine_budget_for(spent)
    assert got == pytest.approx(index.DEADLINE_S - spent)
    assert got < float(index.LIMITS["time_budget_s"])


def test_the_budget_never_goes_below_the_floor():
    """Even a request that has already blown the deadline returns a usable number.

    A negative or tiny budget would have the engine pass start and immediately
    give up, or worse be handed to the analyser as nonsense.
    """
    for spent in (index.DEADLINE_S, index.DEADLINE_S + 30.0, 1e6):
        assert index.engine_budget_for(spent) == index.MIN_ENGINE_BUDGET_S


def test_the_budget_leaves_room_to_answer():
    """The deadline must sit inside the function's own limit, not on top of it."""
    assert index.DEADLINE_S < 60.0
    assert float(index.LIMITS["time_budget_s"]) <= index.DEADLINE_S
