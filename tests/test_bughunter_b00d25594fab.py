from __future__ import annotations

import json

import flightscout.watch as watch_mod
from flightscout.notifiers.base import Notifier


class RecordingNotifier(Notifier):
    name = "public"

    def __init__(self):
        self.subjects = []

    def send(self, subject, html, text):
        self.subjects.append(subject)


def test_regression(tmp_path, monkeypatch):
    watch_id = "bos-bcn-2027-10-09-economy-availability"
    prior_state = {
        watch_id: {
            "notified": True,
            "notified_at": "2026-11-14T12:00:00+00:00",
            "delivered_notifiers": ["public"],
            "error_streak": 2,
            "last_error": "prior failure",
        }
    }
    malformed_state = json.dumps(prior_state) + "\ntrailing malformed data"
    state_path = tmp_path / "state.json"
    state_path.write_text(malformed_state, encoding="utf-8")
    watch = {
        "id": watch_id,
        "type": "availability",
        "origin": "BOS",
        "dest": "BCN",
        "date": "2027-10-09",
        "cabin": "ECONOMY",
        "stops": "ANY",
        "active": True,
    }

    monkeypatch.setattr(watch_mod.config, "state_path", lambda: state_path)
    monkeypatch.setattr(watch_mod, "load_watches", lambda: [watch])
    monkeypatch.setattr(
        watch_mod,
        "evaluate",
        lambda candidate: (True, {"count": 1, "cheapest": None}),
    )
    notifier = RecordingNotifier()

    result = watch_mod.check_watches(
        [notifier], notify=True, record_history=False, persist=True
    )

    assert notifier.subjects == []
    assert state_path.read_text(encoding="utf-8") == malformed_state
    assert result == {
        "checked": 1,
        "fired": [],
        "results": [{"id": watch_id, "status": "state_error"}],
    }
