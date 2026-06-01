"""Telegram notifier: posts the alert via the Bot API sendMessage endpoint."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import Notifier, register


def _post(url: str, payload: dict, headers: dict | None = None) -> None:
    data = json.dumps(payload).encode()
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"POST {url} returned {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"POST {url} failed {e.code}: {body}") from e


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, cfg: dict) -> None:
        token = cfg.get("token")
        chat_id = cfg.get("chat_id")
        if not token:
            raise ValueError("telegram notifier requires 'token'")
        if not chat_id:
            raise ValueError("telegram notifier requires 'chat_id'")
        self.token = token
        self.chat_id = chat_id

    @classmethod
    def from_config(cls, cfg: dict) -> "TelegramNotifier":
        return cls(cfg)

    def send(self, subject: str, html: str, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": subject + "\n\n" + (text or ""),
            "disable_web_page_preview": False,
        }
        _post(url, payload)


@register("telegram")
def _factory(cfg: dict) -> TelegramNotifier:
    return TelegramNotifier.from_config(cfg)
