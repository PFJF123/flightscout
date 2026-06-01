"""Tests for flightscout.history — fare logging + the book-now signal."""
from __future__ import annotations

from datetime import date, timedelta

from flightscout import history


def test_record_appends_one_point_per_day():
    history.record("w1", 400.0, on="2026-06-01")
    history.record("w1", 380.0, on="2026-06-02")
    s = history.series("w1")
    assert [(p["date"], p["price"]) for p in s] == [
        ("2026-06-01", 400.0), ("2026-06-02", 380.0)]


def test_record_same_day_updates_not_appends():
    history.record("w1", 400.0, on="2026-06-01")
    history.record("w1", 350.0, on="2026-06-01")  # same day -> overwrite
    s = history.series("w1")
    assert len(s) == 1
    assert s[0]["price"] == 350.0


def test_record_none_price_is_noop():
    history.record("w1", None)
    assert history.series("w1") == []


def _seed(prices, *, watch="w1", start="2026-05-01"):
    d0 = date.fromisoformat(start)
    for i, p in enumerate(prices):
        history.record(watch, p, on=(d0 + timedelta(days=i)).isoformat())


def test_signal_empty_with_too_few_samples():
    _seed([400.0, 410.0])  # only 2 points
    assert history.signal("w1", 405.0) == {}


def test_signal_returns_empty_when_current_none():
    _seed([400.0, 410.0, 420.0])
    assert history.signal("w1", None) == {}


def test_signal_good_deal_at_minus_ten_pct():
    # median = 400; current 360 -> -10% exactly -> good_deal
    _seed([400.0, 400.0, 400.0])
    sig = history.signal("w1", 360.0)
    assert sig["median"] == 400.0
    assert sig["vs_median_pct"] == -10.0
    assert sig["verdict"] == "good_deal"


def test_signal_high_at_plus_ten_pct():
    _seed([400.0, 400.0, 400.0])
    sig = history.signal("w1", 440.0)
    assert sig["vs_median_pct"] == 10.0
    assert sig["verdict"] == "high"


def test_signal_typical_in_band():
    _seed([400.0, 400.0, 400.0])
    sig = history.signal("w1", 405.0)
    assert sig["verdict"] == "typical"
    assert sig["low"] == 400.0
    assert sig["high"] == 400.0
    assert sig["samples"] == 3
