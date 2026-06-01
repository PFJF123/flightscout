"""Regression tests for the post-launch debug pass (C1, C3, H3, ntfy header)."""
from __future__ import annotations

import os
import sys

import pytest

import flightscout.search  # noqa: F401
from flightscout import FliError, add_watch, multi_airport
from flightscout.config import state_path
from flightscout.notifiers.base import Notifier, send_all
from flightscout.notifiers.ntfy import _ascii_title
from flightscout.watch import check_watches, load_state

search_mod = sys.modules["flightscout.search"]


def _bookable(count=2, price=400.0):
    return {
        "success": True, "count": count,
        "flights": [{
            "price": price, "currency": "USD", "stops": 0, "duration": 480,
            "legs": [{
                "departure_airport": {"code": "BOS"}, "arrival_airport": {"code": "BCN"},
                "departure_time": "2026-09-15T10:00", "arrival_time": "2026-09-15T22:00",
                "duration": 480, "airline": {"code": "IB", "name": "Iberia"}, "flight_number": "1",
            }],
        }] * count,
    }


class _Collecting(Notifier):
    name = "collect"
    def __init__(self, cfg=None): self.msgs = []
    def send(self, subject, html, text): self.msgs.append(subject)


class _Failing(Notifier):
    name = "fail"
    def __init__(self, cfg=None): pass
    def send(self, subject, html, text): raise RuntimeError("boom")


# ---- C3: multi_airport must raise, not report "no flights", when ALL pairs fail
def test_multi_airport_all_fail_raises(monkeypatch):
    def boom(*a, **k):
        raise FliError("rate-limited")
    monkeypatch.setattr(search_mod, "run_fli", boom)
    with pytest.raises(FliError):
        multi_airport(["BOS", "PVD"], ["BCN"], "2026-09-15")


# ---- C2: ntfy Title must be latin-1 safe (no emoji/arrow crash)
def test_ntfy_ascii_title():
    out = _ascii_title("✈ Bookable now: BOS→BCN 2027-05-09")
    out.encode("latin-1")  # must not raise
    assert "->" in out and "✈" not in out


# ---- C1: a notify run that delivers to NOBODY must not latch `notified`
def test_failing_notifier_does_not_latch(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli", lambda *a, **k: _bookable())
    add_watch("availability", "BOS", "BCN", "2026-09-15")
    r = check_watches([_Failing()], notify=True)  # only notifier raises
    wid = "bos-bcn-2026-09-15-economy-availability"
    assert wid in r["fired"]
    assert load_state()[wid].get("notified") is not True  # retries next run


def test_delivery_latches_and_is_once(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli", lambda *a, **k: _bookable())
    add_watch("availability", "BOS", "BCN", "2026-09-15")
    note = _Collecting()
    r1 = check_watches([note], notify=True)
    assert r1["fired"] and load_state()["bos-bcn-2026-09-15-economy-availability"]["notified"] is True
    assert note.msgs  # actually delivered
    r2 = check_watches([note], notify=True)  # second run: already done, no re-send
    assert len(note.msgs) == 1
    assert r2["results"][0]["status"] == "done"


# ---- H3: persist=False must not write state to disk
def test_persist_false_writes_nothing(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli", lambda *a, **k: _bookable())
    add_watch("availability", "BOS", "BCN", "2026-09-15")
    os.path.exists(state_path()) and os.remove(state_path())
    check_watches(notify=False, record_history=False, persist=False)
    assert not os.path.exists(state_path())


# ---- send_all empty list is a no-op (delivered to nobody), not a success
def test_send_all_empty_is_noop():
    assert send_all([], "s", "h", "t") == {}
