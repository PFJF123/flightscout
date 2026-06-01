"""ntfy notifier: posts the alert to an ntfy.sh-style topic."""
from __future__ import annotations

from .base import Notifier, post, register


def _ascii_title(s: str) -> str:
    # HTTP headers are latin-1; ntfy's Title header chokes on emoji/arrows. Fold to ASCII.
    return s.replace("→", "->").replace("✈", "").encode("ascii", "ignore").decode().strip()


@register("ntfy")
class NtfyNotifier(Notifier):
    name = "ntfy"

    def __init__(self, cfg: dict) -> None:
        self.topic = cfg.get("topic")
        if not self.topic:
            raise ValueError("ntfy notifier requires 'topic'")
        self.server = cfg.get("server", "https://ntfy.sh").rstrip("/")
        self.priority = cfg.get("priority")
        self.click = cfg.get("click")

    def send(self, subject: str, html: str, text: str) -> None:
        headers = {"Title": _ascii_title(subject)}
        if self.priority is not None:
            headers["Priority"] = str(self.priority)
        if self.click:
            headers["Click"] = self.click
        post(f"{self.server}/{self.topic}", (text or subject).encode(), headers=headers)
