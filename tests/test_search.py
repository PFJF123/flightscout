"""Tests for flightscout.search — search/cheapest_dates/flexible/multi_airport.

run_fli is bound into search.py, so we patch flightscout.search.run_fli.
"""
from __future__ import annotations

import sys
import urllib.parse

import pytest

import flightscout.search  # noqa: F401  (ensure submodule is imported)
from flightscout import FliError
from flightscout.search import (cheapest_dates, flexible, multi_airport,
                                search)

search_mod = sys.modules["flightscout.search"]


def test_search_parses_count_and_best(monkeypatch, fli_resp):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: fli_resp(2, price=350.0))
    res = search("BOS", "BCN", "2026-10-09")
    assert res.count == 2
    assert res.bookable is True
    assert res.best.price == 350.0
    assert res.route == "BOS->BCN"
    assert res.cabin == "ECONOMY"


def test_search_book_url_is_google_travel_and_contains_date(monkeypatch, fli_resp):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: fli_resp(1))
    res = search("BOS", "BCN", "2026-10-09")
    assert res.book_url.startswith("https://www.google.com/travel/flights?q=")
    # date survives URL-encoding
    assert "2026-10-09" in urllib.parse.unquote(res.book_url)
    assert "one way" in urllib.parse.unquote(res.book_url)


def test_search_round_trip_sets_return_date_and_passes_return(monkeypatch, fli_resp):
    recorded = {}

    def fake(args, *a, **k):
        recorded["args"] = args
        return fli_resp(1)

    monkeypatch.setattr(search_mod, "run_fli", fake)
    res = search("BOS", "BCN", "2026-10-09", return_date="2026-10-16")
    assert res.return_date == "2026-10-16"
    assert "--return" in recorded["args"]
    i = recorded["args"].index("--return")
    assert recorded["args"][i + 1] == "2026-10-16"
    # book_url reflects round-trip
    assert "returning 2026-10-16" in urllib.parse.unquote(res.book_url)


def test_search_limit_trims_flights(monkeypatch, fli_resp):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: fli_resp(10))
    res = search("BOS", "BCN", "2026-10-09", limit=3)
    assert res.count == 10
    assert len(res.flights) == 3


def test_cheapest_dates_parses_rows(monkeypatch, dates_resp):
    monkeypatch.setattr(
        search_mod, "run_fli",
        lambda *a, **k: dates_resp([("2026-10-08", 380.0), ("2026-10-09", 400.0)]),
    )
    rows = cheapest_dates("BOS", "BCN", "2026-10-08", "2026-10-12")
    assert [r.date for r in rows] == ["2026-10-08", "2026-10-09"]
    assert rows[0].price == 380.0


def test_cheapest_dates_raises_fli_error_on_missing_dates_key(monkeypatch):
    # Shape guard: a flights-shaped response (no "dates") must raise FliError.
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: {"success": True, "count": 0, "flights": []})
    with pytest.raises(FliError):
        cheapest_dates("BOS", "BCN", "2026-10-08", "2026-10-12")


def test_flexible_computes_window_and_returns_rows(monkeypatch, dates_resp):
    recorded = {}

    def fake(args, *a, **k):
        recorded["args"] = args
        return dates_resp([("2026-10-06", 360.0), ("2026-10-09", 400.0),
                           ("2026-10-12", 420.0)])

    monkeypatch.setattr(search_mod, "run_fli", fake)
    rows = flexible("BOS", "BCN", "2026-10-09", window=3)
    args = recorded["args"]
    # window=3 around 10-09 -> from 10-06 to 10-12
    assert args[0] == "dates"
    fi = args.index("--from")
    ti = args.index("--to")
    assert args[fi + 1] == "2026-10-06"
    assert args[ti + 1] == "2026-10-12"
    assert len(rows) == 3


def test_multi_airport_merges_and_sorts_ascending(monkeypatch):
    # Make each origin return a different price so we can verify the merge+sort.
    prices = {"BOS": 500.0, "PVD": 300.0}

    def fake(args, *a, **k):
        origin = args[1]
        p = prices[origin]
        return {
            "success": True, "count": 1,
            "flights": [{
                "price": p, "currency": "USD", "stops": 0, "duration": 405,
                "legs": [{"departure_airport": {"code": origin},
                          "arrival_airport": {"code": "BCN"},
                          "airline": {"code": "IB", "name": "Iberia"}}],
            }],
        }

    monkeypatch.setattr(search_mod, "run_fli", fake)
    res = multi_airport(["BOS", "PVD"], ["BCN"], "2026-10-09")
    assert res.count == 2
    # ascending by price -> PVD's 300 first
    assert [f.price for f in res.flights] == [300.0, 500.0]
    assert res.flights[0].legs[0].origin == "PVD"
    assert res.route == "BOS/PVD->BCN"


def test_multi_airport_skips_failing_pair(monkeypatch):
    def fake(args, *a, **k):
        origin = args[1]
        if origin == "BOS":
            raise FliError("boom")
        return {"success": True, "count": 1, "flights": [{
            "price": 250.0, "currency": "USD", "stops": 0, "duration": 405,
            "legs": [{"departure_airport": {"code": origin},
                      "arrival_airport": {"code": "BCN"},
                      "airline": {"code": "IB", "name": "Iberia"}}]}]}

    monkeypatch.setattr(search_mod, "run_fli", fake)
    res = multi_airport(["BOS", "PVD"], ["BCN"], "2026-10-09")
    # BOS raised and was skipped; only PVD's flight survives.
    assert res.count == 1
    assert res.flights[0].legs[0].origin == "PVD"
