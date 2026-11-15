"""Regression test for past targets being reported as bookable."""
from datetime import date, timedelta
import sys

import flightscout.frontier  # noqa: F401
from flightscout.frontier import frontier

frontier_mod = sys.modules["flightscout.frontier"]


def test_regression(monkeypatch):
    today = date.today()
    available_through = today + timedelta(days=200)

    def fake_run_fli(args, *unused_args, **unused_kwargs):
        queried = date.fromisoformat(args[3])
        return {"count": 3 if queried <= available_through else 0}

    monkeypatch.setattr(frontier_mod, "run_fli", fake_run_fli)
    monkeypatch.setattr(frontier_mod.time, "sleep", lambda *args, **kwargs: None)

    target = (today - timedelta(days=1)).isoformat()
    result = frontier("BOS", "BCN", target=target, sleep=0)

    assert result["target"]["bookable_now"] is False
