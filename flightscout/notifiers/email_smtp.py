"""Email notifier: sends a multipart/alternative (text + html) over SMTP."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .base import Notifier, register


class EmailNotifier(Notifier):
    name = "email"

    def __init__(self, cfg: dict) -> None:
        host = cfg.get("host")
        to_addr = cfg.get("to_addr")
        if not host:
            raise ValueError("email notifier requires 'host'")
        if not to_addr:
            raise ValueError("email notifier requires 'to_addr'")
        self.host = host
        self.port = int(cfg.get("port", 587))
        self.username = cfg.get("username")
        self.password = cfg.get("password")
        self.from_addr = cfg.get("from_addr") or self.username or to_addr
        self.to_addr = to_addr
        self.use_tls = bool(cfg.get("use_tls", True))

    @classmethod
    def from_config(cls, cfg: dict) -> "EmailNotifier":
        return cls(cfg)

    def send(self, subject: str, html: str, text: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        msg.set_content(text or "")
        msg.add_alternative(html or "", subtype="html")

        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)


@register("email")
def _factory(cfg: dict) -> EmailNotifier:
    return EmailNotifier.from_config(cfg)
