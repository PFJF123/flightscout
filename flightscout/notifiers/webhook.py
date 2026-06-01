"""Webhook notifier: posts the full (subject, html, text) payload as JSON to a URL."""
from __future__ import annotations

import json

from .base import Notifier, post, register


@register("webhook")
class WebhookNotifier(Notifier):
    name = "webhook"

    def __init__(self, cfg: dict) -> None:
        self.url = cfg.get("url")
        if not self.url:
            raise ValueError("webhook notifier requires 'url'")
        self.method = cfg.get("method", "POST")
        self.headers = {"Content-Type": "application/json", **dict(cfg.get("headers") or {})}

    def send(self, subject: str, html: str, text: str) -> None:
        body = json.dumps({"subject": subject, "html": html, "text": text}).encode()
        post(self.url, body, headers=self.headers, method=self.method)
