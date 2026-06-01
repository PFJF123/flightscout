"""Tests for flightscout.watch — CRUD + check_watches reliability model.

watch.evaluate calls search.search, which uses run_fli bound into search.py,
so we patch flightscout.search.run_fli to mock the fli layer.
"""
from __future__ import annotations

import sys

import pytest

from flightscout import (add_watch, check_watches, list_watches, remove_watch)
from flightscout.notifiers.base import Notifier
from flightscout.state import load_json, save_json
from flightscout import config
import flightscout.search  # noqa: F401  (ensure submodule is imported)

# flightscout.__init__ re-exports the `search` *function* onto the package, which
# shadows the submodule attribute; grab the real module object from sys.modules.
search_mod = sys.modules["flightscout.search"]


class CollectingNotifier(Notifier):
    """In-memory notifier that records every delivery."""
    name = "collect"

    def __init__(self):
        self.messages = []

    def send(self, subject, html, text):
        self.messages.append((subject, html, text))


class FailingNotifier(Notifier):
    name = "fail"

    def send(self, subject, html, text):
        raise RuntimeError("delivery boom")


def _avail_resp(count, price=400.0):
    return {
        "success": True, "count": count,
        "flights": [{
            "price": price, "currency": "USD", "stops": 0, "duration": 405,
            "legs": [{"departure_airport": {"code": "BOS"},
                      "arrival_airport": {"code": "BCN"},
                      "departure_time": "2026-10-09T18:30",
                      "arrival_time": "2026-10-10T08:15",
                      "duration": 405,
                      "airline": {"code": "IB", "name": "Iberia"}}],
        } for _ in range(count)],
    }


# ---------------------------------------------------------------- CRUD
def test_add_list_remove_round_trip():
    w = add_watch("availability", "BOS", "BCN", "2026-10-09")
    assert w["id"] == "bos-bcn-2026-10-09-economy-availability"
    assert [x["id"] for x in list_watches()] == [w["id"]]

    assert remove_watch(w["id"]) is True
    assert list_watches() == []
    # removing a non-existent watch returns False
    assert remove_watch("does-not-exist") is False


def test_remove_watch_clears_state():
    w = add_watch("availability", "BOS", "BCN", "2026-10-09")
    # seed some state for the watch
    save_json(config.state_path(), {w["id"]: {"last_check": "2026-06-01"}})
    assert remove_watch(w["id"]) is True
    assert load_json(config.state_path(), {}) == {}


def test_add_price_watch_requires_threshold():
    with pytest.raises(ValueError):
        add_watch("price", "BOS", "BCN", "2026-10-09")


def test_add_rejects_bad_type():
    with pytest.raises(ValueError):
        add_watch("bogus", "BOS", "BCN", "2026-10-09")


def test_add_rejects_duplicate():
    add_watch("availability", "BOS", "BCN", "2026-10-09")
    with pytest.raises(ValueError):
        add_watch("availability", "BOS", "BCN", "2026-10-09")


# ---------------------------------------------------------------- fire-once
def test_availability_fires_once_then_done(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return _avail_resp(3)

    monkeypatch.setattr(search_mod, "run_fli", fake)
    note = CollectingNotifier()
    w = add_watch("availability", "BOS", "BCN", "2026-10-09")

    r1 = check_watches([note], notify=True)
    assert w["id"] in r1["fired"]
    assert len(note.messages) == 1
    after_first = calls["n"]
    assert after_first >= 1

    # Second run: watch is latched 'done', so evaluate() is NOT called again.
    r2 = check_watches([note], notify=True)
    assert r2["fired"] == []
    statuses = {row["id"]: row.get("status") for row in r2["results"]}
    assert statuses[w["id"]] == "done"
    assert calls["n"] == after_first          # no further fli calls
    assert len(note.messages) == 1            # no re-delivery


# ---------------------------------------------------------------- error path
def test_error_streak_escalates_once(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("rate-limited")

    monkeypatch.setattr(search_mod, "run_fli", boom)
    note = CollectingNotifier()
    add_watch("availability", "BOS", "BCN", "2026-10-09")

    check_watches([note], notify=True)  # streak 1
    check_watches([note], notify=True)  # streak 2
    r3 = check_watches([note], notify=True)  # streak 3 -> escalate

    state = load_json(config.state_path(), {})
    st = next(iter(state.values()))
    assert st["error_streak"] == 3
    # escalation fired exactly once
    assert any(row.get("error_escalated") for row in r3["results"])
    assert len(note.messages) == 1
    subject = note.messages[0][0]
    assert "Watch may be broken" in subject

    # A 4th errored run does NOT re-escalate (error_alerted latched).
    check_watches([note], notify=True)
    assert len(note.messages) == 1


# ---------------------------------------------------------------- state prune
def test_stale_state_key_pruned(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: _avail_resp(0))
    w = add_watch("availability", "BOS", "BCN", "2026-10-09")
    # Inject a stale key for a watch that no longer exists.
    s = load_json(config.state_path(), {})
    s["ghost-watch-id"] = {"last_check": "2026-01-01"}
    save_json(config.state_path(), s)

    check_watches([], notify=False)
    after = load_json(config.state_path(), {})
    assert "ghost-watch-id" not in after
    assert w["id"] in after


# ---------------------------------------------------------------- corrupt state
def test_corrupt_state_is_tolerated(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: _avail_resp(0))
    add_watch("availability", "BOS", "BCN", "2026-10-09")
    # Write garbage directly to the state file.
    with open(config.state_path(), "w") as fh:
        fh.write("{not valid json at all]")

    # load_json returns {} on corruption, so the run must still complete.
    report = check_watches([], notify=False)
    assert report["checked"] == 1


# ---------------------------------------------------------------- delivery + notify failure
def test_notify_exception_does_not_set_notified(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: _avail_resp(2))
    w = add_watch("availability", "BOS", "BCN", "2026-10-09")

    # A single failing notifier -> send_all raises (all failed) -> caught,
    # 'notified' must NOT be set so the alert retries next run.
    r = check_watches([FailingNotifier()], notify=True)
    assert w["id"] in r["fired"]
    state = load_json(config.state_path(), {})
    st = state[w["id"]]
    assert st.get("notified") is not True
    assert st.get("fire_detected_at")  # detection latched even though send failed

    # Now a working notifier on the retry delivers and latches 'notified'.
    note = CollectingNotifier()
    check_watches([note], notify=True)
    assert len(note.messages) == 1
    st2 = load_json(config.state_path(), {})[w["id"]]
    assert st2.get("notified") is True


def test_price_watch_fires_below_threshold(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: _avail_resp(1, price=320.0))
    note = CollectingNotifier()
    w = add_watch("price", "BOS", "BCN", "2026-10-09", threshold=400.0)
    r = check_watches([note], notify=True)
    assert w["id"] in r["fired"]
    assert len(note.messages) == 1
    assert "Fare drop" in note.messages[0][0]


def test_price_watch_does_not_fire_above_threshold(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli",
                        lambda *a, **k: _avail_resp(1, price=500.0))
    note = CollectingNotifier()
    add_watch("price", "BOS", "BCN", "2026-10-09", threshold=400.0)
    r = check_watches([note], notify=True)
    assert r["fired"] == []
    assert note.messages == []
