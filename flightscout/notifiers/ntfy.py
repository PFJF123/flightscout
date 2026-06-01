"""ntfy notifier: posts the alert to an ntfy.sh-style topic."""
from __future__ import annotations

import urllib.error
import urllib.request

from .base import Notifier, register


def _post(url: str, data: bytes, headers: dict | None = None) -> None:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"POST {url} returned {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"POST {url} failed {e.code}: {body}") from e


class NtfyNotifier(Notifier):
    name = "ntfy"

    def __init__(self, cfg: dict) -> None:
        topic = cfg.get("topic")
        if not topic:
            raise ValueError("ntfy notifier requires 'topic'")
        self.topic = topic
        self.server = cfg.get("server", "https://ntfy.sh").rstrip("/")
        self.priority = cfg.get("priority")
        self.click = cfg.get("click")

    @classmethod
    def from_config(cls, cfg: dict) -> "NtfyNotifier":
        return cls(cfg)

    def send(self, subject: str, html: str, text: str) -> None:
        url = f"{self.server}/{self.topic}"
        headers = {"Title": subject}
        if self.priority is not None:
            headers["Priority"] = str(self.priority)
        if self.click:
            headers["Click"] = self.click
        _post(url, (text or "").encode(), headers)


@register("ntfy")
def _factory(cfg: dict) -> NtfyNotifier:
    return NtfyNotifier.from_config(cfg)
