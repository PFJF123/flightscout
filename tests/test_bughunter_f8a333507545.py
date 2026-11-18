from __future__ import annotations

import importlib

from flightscout.notifiers.base import Notifier
from flightscout.state import load_json

watch_mod = importlib.import_module("flightscout.watch")


def test_regression(monkeypatch, tmp_path):
    class EmailNotifier(Notifier):
        name = "email"

        def __init__(self):
            self.calls = 0

        def send(self, subject, html, text):
            self.calls += 1

    class RecoveringTelegramNotifier(Notifier):
        name = "telegram"

        def __init__(self):
            self.calls = 0

        def send(self, subject, html, text):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary outage")

    state_path = tmp_path / "state.json"
    watch = {
        "id": "dead-man",
        "type": "availability",
        "origin": "BOS",
        "dest": "BCN",
        "date": "2026-10-09",
        "active": True,
    }
    email = EmailNotifier()
    telegram = RecoveringTelegramNotifier()

    monkeypatch.setattr(watch_mod.config, "state_path", lambda: str(state_path))
    monkeypatch.setattr(watch_mod, "load_watches", lambda: [watch])
    monkeypatch.setattr(watch_mod, "evaluate", lambda _watch: (False, {"error": "search unavailable"}))
    monkeypatch.setattr(watch_mod, "ERROR_ALERT_THRESHOLD", 1)

    watch_mod.check_watches(
        notifiers=[email, telegram], notify=True, record_history=False
    )
    watch_mod.check_watches(
        notifiers=[email, telegram], notify=True, record_history=False
    )

    state = load_json(str(state_path), {})["dead-man"]
    assert email.calls == 1
    assert telegram.calls == 2
    assert state["error_alerted"] is True
    assert set(state["error_delivered_notifiers"]) == {"email", "telegram"}
