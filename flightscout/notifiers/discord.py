"""Discord notifier: posts the alert to a channel webhook."""
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


class DiscordNotifier(Notifier):
    name = "discord"

    def __init__(self, cfg: dict) -> None:
        webhook_url = cfg.get("webhook_url")
        if not webhook_url:
            raise ValueError("discord notifier requires 'webhook_url'")
        self.webhook_url = webhook_url

    @classmethod
    def from_config(cls, cfg: dict) -> "DiscordNotifier":
        return cls(cfg)

    def send(self, subject: str, html: str, text: str) -> None:
        content = (subject + "\n\n" + (text or ""))[:1900]
        _post(self.webhook_url, {"content": content})


@register("discord")
def _factory(cfg: dict) -> DiscordNotifier:
    return DiscordNotifier.from_config(cfg)
