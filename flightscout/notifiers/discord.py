"""Discord notifier: posts the alert to a channel webhook."""
from __future__ import annotations

import json

from .base import Notifier, post, register


@register("discord")
class DiscordNotifier(Notifier):
    name = "discord"

    def __init__(self, cfg: dict) -> None:
        self.webhook_url = cfg.get("webhook_url")
        if not self.webhook_url:
            raise ValueError("discord notifier requires 'webhook_url'")

    def send(self, subject: str, html: str, text: str) -> None:
        content = (subject + "\n\n" + (text or ""))[:1900]
        post(self.webhook_url, json.dumps({"content": content}).encode(),
             headers={"Content-Type": "application/json"})
