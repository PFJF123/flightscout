"""Shared fixtures for the flightscout test suite.

No network: the `fli` layer is mocked everywhere. `run_fli` is bound INTO
`search.py` (`from ._fli import run_fli`) and `frontier.py`
(`from ._fli import FliError, run_fli`), so tests monkeypatch the name where it
is USED, e.g. `monkeypatch.setattr("flightscout.search.run_fli", fake)`.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def tmp_home(monkeypatch, tmp_path):
    """Isolate every test: point FLIGHTSCOUT_HOME at a fresh tmp dir so
    watches/state/history never touch the real ~/.flightscout."""
    home = tmp_path / "fshome"
    home.mkdir()
    monkeypatch.setenv("FLIGHTSCOUT_HOME", str(home))
    # Make sure no stray config file leaks in from the cwd / env.
    monkeypatch.delenv("FLIGHTSCOUT_CONFIG", raising=False)
    return home


def _leg(origin="BOS", dest="BCN", airline_code="IB", airline_name="Iberia"):
    return {
        "departure_airport": {"code": origin},
        "arrival_airport": {"code": dest},
        "departure_time": "2026-10-09T18:30",
        "arrival_time": "2026-10-10T08:15",
        "duration": 405,
        "airline": {"code": airline_code, "name": airline_name},
        "flight_number": f"{airline_code}1234",
    }


def _flight(price=400.0, currency="USD", stops=0, duration=405,
            origin="BOS", dest="BCN"):
    return {
        "price": price,
        "currency": currency,
        "stops": stops,
        "duration": duration,
        "legs": [_leg(origin=origin, dest=dest)],
    }


@pytest.fixture
def fli_resp():
    """Build a canned `fli flights` response dict with `count` flights."""
    def make(count, price=400.0, *, currency="USD", stops=0,
             origin="BOS", dest="BCN"):
        return {
            "success": True,
            "count": count,
            "flights": [
                _flight(price=price, currency=currency, stops=stops,
                        origin=origin, dest=dest)
                for _ in range(count)
            ],
        }
    return make


@pytest.fixture
def dates_resp():
    """Build a canned `fli dates` response dict.

    Pass a list of (departure_date, price) tuples, or rely on defaults.
    """
    def make(rows=None, *, currency="USD", return_date=None):
        if rows is None:
            rows = [("2026-10-08", 380.0), ("2026-10-09", 400.0)]
        return {
            "success": True,
            "dates": [
                {
                    "departure_date": d,
                    "price": p,
                    "currency": currency,
                    "return_date": return_date,
                }
                for (d, p) in rows
            ],
        }
    return make
