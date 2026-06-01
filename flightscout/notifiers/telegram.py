"""Telegram notifier: posts the alert via the Bot API sendMessage endpoint."""
from __future__ import annotations

import json

from .base import Notifier, post, register


@register("telegram")
class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, cfg: dict) -> None:
        self.token = cfg.get("token")
        self.chat_id = cfg.get("chat_id")
        if not self.token or not self.chat_id:
            raise ValueError("telegram notifier requires 'token' and 'chat_id'")

    def send(self, subject: str, html: str, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": subject + "\n\n" + (text or "")}
        post(url, json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
