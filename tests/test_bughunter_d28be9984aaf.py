"""A successful airport pair must not hide failed comparisons."""
from __future__ import annotations

import importlib

from flightscout import FliError

search_mod = importlib.import_module("flightscout.search")


def test_regression(monkeypatch):
    def fake(args):
        if args[1] == "BOS":
            raise FliError("rate-limited 429")
        return {"count": 1, "flights": [{"price": 250.0}]}

    monkeypatch.setattr(search_mod, "run_fli", fake)
    result = search_mod.multi_airport(["BOS", "PVD"], ["BCN"], "2026-11-22")
    payload = result.to_dict()
    assert payload.get("incomplete") is True
    assert payload["failed_pairs"] == [
        {"origin": "BOS", "dest": "BCN", "error": "rate-limited 429"}
    ]
    assert result.bookable is True
    assert [flight.price for flight in result.flights] == [250.0]
