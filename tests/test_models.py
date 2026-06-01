"""Tests for flightscout.models — Flight/Leg/DateFare/SearchResult."""
from __future__ import annotations

from flightscout.models import DateFare, Flight, Leg, SearchResult


def _two_leg_flight():
    f = {
        "price": 512.0,
        "currency": "USD",
        "stops": 1,
        "duration": 750,  # 12h30m
        "legs": [
            {
                "departure_airport": {"code": "BOS"},
                "arrival_airport": {"code": "LIS"},
                "departure_time": "2026-10-09T18:30",
                "arrival_time": "2026-10-10T06:00",
                "duration": 360,
                "airline": {"code": "TP", "name": "TAP Air Portugal"},
                "flight_number": "TP216",
            },
            {
                "departure_airport": {"code": "LIS"},
                "arrival_airport": {"code": "BCN"},
                "departure_time": "2026-10-10T07:30",
                "arrival_time": "2026-10-10T11:00",
                "duration": 120,
                "airline": {"code": "TP", "name": "TAP Air Portugal"},
                "flight_number": "TP1042",
            },
        ],
    }
    return Flight.from_fli(f)


def test_flight_from_fli_basic_fields():
    f = Flight.from_fli({"price": 400.0, "currency": "EUR", "stops": 0,
                         "duration": 405, "legs": []})
    assert f.price == 400.0
    assert f.currency == "EUR"
    assert f.stops == 0
    assert f.duration_min == 405
    assert f.legs == []


def test_flight_currency_defaults_usd():
    f = Flight.from_fli({"price": 100.0})
    assert f.currency == "USD"


def test_flight_airlines_dedupes_preserving_order():
    f = _two_leg_flight()
    # Both legs are TAP -> deduped to one entry.
    assert f.airlines == ["TAP Air Portugal"]


def test_flight_via_for_connection():
    f = _two_leg_flight()
    # via = dest of every leg except the last -> the connection point.
    assert f.via == ["LIS"]


def test_flight_via_empty_for_nonstop():
    f = Flight.from_fli({"price": 1.0, "legs": [
        {"departure_airport": {"code": "BOS"},
         "arrival_airport": {"code": "BCN"},
         "airline": {"code": "IB", "name": "Iberia"}},
    ]})
    assert f.via == []


def test_flight_duration_str():
    f = _two_leg_flight()
    assert f.duration_str == "12h30m"


def test_flight_duration_str_none_when_zero_or_missing():
    assert Flight.from_fli({"price": 1.0, "duration": 0}).duration_str is None
    assert Flight.from_fli({"price": 1.0}).duration_str is None


def test_flight_depart_arrive_span_first_and_last_leg():
    f = _two_leg_flight()
    assert f.depart == "2026-10-09T18:30"
    assert f.arrive == "2026-10-10T11:00"


def test_leg_from_fli_handles_missing_airport_and_airline():
    leg = Leg.from_fli({})
    assert leg.origin is None
    assert leg.dest is None
    assert leg.airline is None
    assert leg.airline_code is None


def test_flight_to_dict_includes_derived_props():
    f = _two_leg_flight()
    d = f.to_dict()
    assert d["airlines"] == ["TAP Air Portugal"]
    assert d["via"] == ["LIS"]
    assert d["duration"] == "12h30m"
    assert d["depart"] == "2026-10-09T18:30"
    assert d["arrive"] == "2026-10-10T11:00"
    # raw dataclass fields still present
    assert d["price"] == 512.0
    assert isinstance(d["legs"], list) and len(d["legs"]) == 2


def test_datefare_from_fli_and_to_dict():
    df = DateFare.from_fli({"departure_date": "2026-10-09", "price": 388.0,
                            "currency": "EUR", "return_date": "2026-10-16"})
    assert df.date == "2026-10-09"
    assert df.price == 388.0
    assert df.currency == "EUR"
    assert df.return_date == "2026-10-16"
    assert df.to_dict() == {
        "date": "2026-10-09", "price": 388.0,
        "currency": "EUR", "return_date": "2026-10-16",
    }


def test_datefare_defaults():
    df = DateFare.from_fli({"departure_date": "2026-10-09", "price": 100.0})
    assert df.currency == "USD"
    assert df.return_date is None


def _result_with(prices):
    flights = [Flight.from_fli({"price": p, "legs": [
        {"departure_airport": {"code": "BOS"},
         "arrival_airport": {"code": "BCN"},
         "airline": {"code": "IB", "name": "Iberia"}}]}) for p in prices]
    return SearchResult(route="BOS->BCN", date="2026-10-09", cabin="ECONOMY",
                        count=len(flights), flights=flights,
                        book_url="https://example/book")


def test_searchresult_best_and_bookable():
    res = _result_with([300.0, 400.0])
    assert res.bookable is True
    assert res.best is not None
    assert res.best.price == 300.0


def test_searchresult_not_bookable_when_count_zero():
    res = SearchResult(route="BOS->BCN", date="2026-10-09", cabin="ECONOMY",
                       count=0, flights=[])
    assert res.bookable is False
    assert res.best is None


def test_searchresult_to_dict_limit():
    res = _result_with([300.0, 400.0, 500.0])
    d = res.to_dict(limit=2)
    assert d["count"] == 3            # count is unaffected by limit
    assert len(d["flights"]) == 2     # but the serialized list is trimmed
    assert d["bookable"] is True
    assert d["best"]["price"] == 300.0
    assert d["book_url"] == "https://example/book"


def test_searchresult_to_dict_no_limit_returns_all():
    res = _result_with([300.0, 400.0, 500.0])
    d = res.to_dict()
    assert len(d["flights"]) == 3
    assert d["best"] is not None
