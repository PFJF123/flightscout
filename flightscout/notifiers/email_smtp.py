"""Email notifier over SMTP (STARTTLS on 587, implicit SSL on 465)."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .base import Notifier, register


@register("email")
class EmailNotifier(Notifier):
    name = "email"

    def __init__(self, cfg: dict) -> None:
        self.host = cfg.get("host")
        self.to_addr = cfg.get("to_addr")
        if not self.host or not self.to_addr:
            raise ValueError("email notifier requires 'host' and 'to_addr'")
        self.port = int(cfg.get("port", 587))
        self.username = cfg.get("username")
        self.password = cfg.get("password")
        self.from_addr = cfg.get("from_addr") or self.username or self.to_addr
        self.use_tls = bool(cfg.get("use_tls", True))

    def send(self, subject: str, html: str, text: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        msg.set_content(text or subject)
        if html:
            msg.add_alternative(html, subtype="html")
        if self.port == 465:  # implicit SSL
            with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as s:
                if self.username:
                    s.login(self.username, self.password or "")
                s.send_message(msg)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=30) as s:
                if self.use_tls:
                    s.starttls()
                if self.username:
                    s.login(self.username, self.password or "")
                s.send_message(msg)
