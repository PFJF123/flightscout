"""Tests for flightscout.frontier — booking-frontier binary search.

run_fli is bound into frontier.py, so we patch flightscout.frontier.run_fli.
We also patch frontier's time.sleep so the binary search runs instantly.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

import pytest

import flightscout.frontier  # noqa: F401  (ensure submodule is imported)
from flightscout import FliError
from flightscout.frontier import frontier

frontier_mod = sys.modules["flightscout.frontier"]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(frontier_mod.time, "sleep", lambda *a, **k: None)


def _flights_count(count):
    return {"success": True, "count": count, "flights": [None] * count}


def test_frontier_finds_cliff_and_estimates_target(monkeypatch):
    today = date.today()
    frontier_day = today + timedelta(days=200)  # availability ends here

    def fake(args, *a, **k):
        queried = date.fromisoformat(args[3])
        return _flights_count(5 if queried <= frontier_day else 0)

    monkeypatch.setattr(frontier_mod, "run_fli", fake)

    target = (today + timedelta(days=260)).isoformat()
    out = frontier("BOS", "BCN", target=target, sleep=0)

    found = date.fromisoformat(out["frontier"])
    # Binary search lands on the cliff within a day.
    assert abs((found - frontier_day).days) <= 1
    assert out["horizon_days"] == (found - today).days

    t = out["target"]
    assert t["date"] == target
    assert t["bookable_now"] is False
    # est_open_date = today + (target - frontier) days.
    days_out = (date.fromisoformat(target) - found).days
    assert t["days_past_frontier"] == days_out
    assert t["est_open_date"] == (today + timedelta(days=days_out)).isoformat()


def test_frontier_target_already_within_frontier(monkeypatch):
    today = date.today()
    frontier_day = today + timedelta(days=300)

    def fake(args, *a, **k):
        queried = date.fromisoformat(args[3])
        return _flights_count(3 if queried <= frontier_day else 0)

    monkeypatch.setattr(frontier_mod, "run_fli", fake)
    target = (today + timedelta(days=50)).isoformat()
    out = frontier("BOS", "BCN", target=target, sleep=0)
    assert out["target"]["bookable_now"] is True


def test_frontier_no_near_term_availability(monkeypatch):
    monkeypatch.setattr(frontier_mod, "run_fli",
                        lambda *a, **k: _flights_count(0))
    out = frontier("BOS", "BCN", sleep=0)
    assert "error" in out
    assert "frontier" not in out


def test_frontier_error_mid_search_returns_frontier_at_least(monkeypatch):
    today = date.today()
    near = (today + timedelta(days=1)).isoformat()

    def fake(args, *a, **k):
        queried = args[3]
        if queried == near:
            return _flights_count(5)  # near-term probe succeeds
        raise FliError("rate-limited (429)")  # every mid probe errors

    monkeypatch.setattr(frontier_mod, "run_fli", fake)
    out = frontier("BOS", "BCN", sleep=0)
    # Error path: must NOT report a (wrong) early frontier date.
    assert "frontier_at_least" in out
    assert out["frontier_at_least"] == near
    assert "frontier" not in out
    assert "error" in out
