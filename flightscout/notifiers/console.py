"""Console notifier: prints the alert to stdout. The zero-config default."""
from __future__ import annotations

import re

from .base import Notifier, register


def _strip_html(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


@register("console")
class ConsoleNotifier(Notifier):
    name = "console"

    def __init__(self, cfg: dict | None = None):
        pass  # console takes no config; accepts cfg so the registry can call factory(cfg)

    @classmethod
    def from_config(cls, cfg: dict) -> "ConsoleNotifier":
        return cls()

    def send(self, subject: str, html: str, text: str) -> None:
        body = text or _strip_html(html)
        print(f"\n=== {subject} ===\n{body}\n")
