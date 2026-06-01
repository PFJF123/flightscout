"""Tests for flightscout.formatting — markdown renderers."""
from __future__ import annotations

from flightscout.formatting import format_dates, format_frontier, format_search
from flightscout.models import DateFare, Flight, SearchResult


def _flight(price=400.0):
    return Flight.from_fli({
        "price": price, "currency": "USD", "stops": 0, "duration": 405,
        "legs": [{"departure_airport": {"code": "BOS"},
                  "arrival_airport": {"code": "BCN"},
                  "departure_time": "2026-10-09T18:30",
                  "arrival_time": "2026-10-10T08:15",
                  "duration": 405,
                  "airline": {"code": "IB", "name": "Iberia"}}],
    })


def test_format_search_bookable():
    res = SearchResult(route="BOS->BCN", date="2026-10-09", cabin="ECONOMY",
                       count=2, flights=[_flight(300.0), _flight(400.0)],
                       book_url="https://book")
    out = format_search(res)
    assert out
    assert "BOS->BCN" in out
    assert "2026-10-09" in out
    assert "Iberia" in out
    assert "Open in Google Flights" in out


def test_format_search_round_trip_shows_return():
    res = SearchResult(route="BOS->BCN", date="2026-10-09", cabin="ECONOMY",
                       count=1, flights=[_flight()], return_date="2026-10-16")
    assert "2026-10-16" in format_search(res)


def test_format_search_not_bookable():
    res = SearchResult(route="BOS->BCN", date="2026-10-09", cabin="ECONOMY",
                       count=0, flights=[])
    out = format_search(res)
    assert out
    assert "Not bookable" in out


def test_format_dates_with_rows_marks_cheapest():
    rows = [DateFare(date="2026-10-08", price=380.0),
            DateFare(date="2026-10-09", price=400.0)]
    out = format_dates(rows)
    assert out
    assert "2026-10-08" in out
    assert "cheapest" in out


def test_format_dates_empty():
    out = format_dates([])
    assert out
    assert "No results" in out


def test_format_frontier_full():
    d = {
        "route": "BOS->BCN", "cabin": "ECONOMY",
        "frontier": "2026-12-01", "horizon_days": 200, "as_of": "2026-06-01",
        "target": {"date": "2027-01-15", "bookable_now": False,
                   "days_past_frontier": 45, "est_open_date": "2026-07-16",
                   "note": "estimate"},
    }
    out = format_frontier(d)
    assert out
    assert "Booking frontier" in out
    assert "2026-12-01" in out
    assert "2026-07-16" in out


def test_format_frontier_bookable_now():
    d = {"route": "BOS->BCN", "cabin": "ECONOMY", "frontier": "2027-04-01",
         "horizon_days": 300, "as_of": "2026-06-01",
         "target": {"date": "2026-07-01", "bookable_now": True}}
    out = format_frontier(d)
    assert "is bookable now" in out


def test_format_frontier_error():
    out = format_frontier({"route": "BOS->BCN",
                           "error": "rate-limited; try again"})
    assert out
    assert "rate-limited" in out
    assert "BOS->BCN" in out
