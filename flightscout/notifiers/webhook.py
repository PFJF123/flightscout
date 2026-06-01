"""Webhook notifier: posts the full (subject, html, text) payload as JSON to a URL."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import Notifier, register


class WebhookNotifier(Notifier):
    name = "webhook"

    def __init__(self, cfg: dict) -> None:
        url = cfg.get("url")
        if not url:
            raise ValueError("webhook notifier requires 'url'")
        self.url = url
        self.method = cfg.get("method", "POST")
        self.headers = dict(cfg.get("headers") or {})

    @classmethod
    def from_config(cls, cfg: dict) -> "WebhookNotifier":
        return cls(cfg)

    def send(self, subject: str, html: str, text: str) -> None:
        body = json.dumps({"subject": subject, "html": html, "text": text}).encode()
        headers = {"Content-Type": "application/json"}
        headers.update(self.headers)
        req = urllib.request.Request(
            self.url, data=body, headers=headers, method=self.method
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status >= 300:
                    raise RuntimeError(f"{self.method} {self.url} returned {resp.status}")
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"{self.method} {self.url} failed {e.code}: {err}") from e


@register("webhook")
def _factory(cfg: dict) -> WebhookNotifier:
    return WebhookNotifier.from_config(cfg)
