"""Tests for flightscout.notifiers — registry, build_notifiers, send_all."""
from __future__ import annotations

import ssl
import urllib.error

import pytest

# Importing the package populates the registry via @register.
import flightscout.notifiers  # noqa: F401
from flightscout.notifiers import build_notifiers, send_all
from flightscout.notifiers.base import Notifier, _REGISTRY
from flightscout.notifiers.base import post
from flightscout.notifiers.email_smtp import EmailNotifier


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


def test_http_errors_do_not_expose_url_credentials(monkeypatch):
    secret_url = "https://api.example.test/webhooks/123/TOP_SECRET_TOKEN"

    def fail(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr("flightscout.notifiers.base.urllib.request.urlopen", fail)
    with pytest.raises(RuntimeError) as exc_info:
        post(secret_url, b"{}")

    message = str(exc_info.value)
    assert "TOP_SECRET_TOKEN" not in message
    assert secret_url not in message
    assert "HTTP 401" in message
    assert "Unauthorized" in message


@pytest.mark.parametrize("port", [465, 587])
def test_smtp_tls_uses_validating_ssl_context(monkeypatch, port):
    sentinel = object()
    observed = {}

    class FakeSMTP:
        def __init__(self, host, actual_port, **kwargs):
            observed["connect"] = (host, actual_port, kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, **kwargs):
            observed["starttls"] = kwargs

        def login(self, username, password):
            pass

        def send_message(self, message):
            pass

    monkeypatch.setattr(ssl, "create_default_context", lambda: sentinel)
    monkeypatch.setattr("flightscout.notifiers.email_smtp.smtplib.SMTP_SSL", FakeSMTP)
    monkeypatch.setattr("flightscout.notifiers.email_smtp.smtplib.SMTP", FakeSMTP)
    notifier = EmailNotifier({"host": "smtp.example", "port": port, "to_addr": "to@example.test"})

    notifier.send("subject", "<p>body</p>", "body")

    if port == 465:
        assert observed["connect"][2]["context"] is sentinel
    else:
        assert observed["starttls"]["context"] is sentinel
