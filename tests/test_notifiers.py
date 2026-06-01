"""Tests for flightscout.notifiers — registry, build_notifiers, send_all."""
from __future__ import annotations

import pytest

# Importing the package populates the registry via @register.
import flightscout.notifiers  # noqa: F401
from flightscout.notifiers import build_notifiers, send_all
from flightscout.notifiers.base import Notifier, _REGISTRY


def test_registry_has_all_builtin_notifiers():
    for name in ("console", "email", "telegram", "discord", "ntfy", "webhook"):
        assert name in _REGISTRY


def test_build_notifiers_skips_unknown(capsys):
    out = build_notifiers({"console": {}, "nope-not-real": {"foo": 1}})
    names = [n.name for n in out]
    assert "console" in names
    assert all(n.name != "nope-not-real" for n in out)
    err = capsys.readouterr().err
    assert "unknown notifier 'nope-not-real'" in err


def test_build_notifiers_skips_misconfigured(capsys):
    # email requires host + to_addr; an empty dict raises -> skipped, no crash.
    out = build_notifiers({"email": {}})
    assert out == []
    assert "misconfigured" in capsys.readouterr().err


def test_build_notifiers_respects_enabled_false():
    out = build_notifiers({"console": {"enabled": False}})
    assert out == []


class OK(Notifier):
    name = "ok"

    def send(self, subject, html, text):
        pass


class Boom(Notifier):
    name = "boom"

    def send(self, subject, html, text):
        raise RuntimeError("nope")


def test_send_all_per_notifier_results():
    res = send_all([OK()], "s", "<p>h</p>", "t")
    assert res == {"ok": True}


def test_send_all_partial_failure_does_not_raise():
    res = send_all([OK(), Boom()], "s", "h", "t")
    assert res["ok"] is True
    assert "nope" in res["boom"]


def test_send_all_raises_when_all_fail():
    with pytest.raises(RuntimeError):
        send_all([Boom()], "s", "h", "t")


def test_send_all_empty_list_is_noop():
    # No notifiers configured -> returns {}, does not raise.
    assert send_all([], "s", "h", "t") == {}
