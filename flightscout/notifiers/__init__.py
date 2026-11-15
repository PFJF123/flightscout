"""Notifier registry. Importing a notifier module registers it via @register.

Network notifiers are imported defensively so a missing/optional one never breaks
the package import.
"""
from __future__ import annotations

from . import console  # noqa: F401  (always available)
from .base import Notifier, build_notifiers, register, send_all

for _m in ("email_smtp", "telegram", "discord", "ntfy", "webhook"):
    try:
        __import__(f"{__name__}.{_m}")
    except Exception:  # noqa: BLE001, S110 - Optional imports must not break the package.
        pass

__all__ = ["Notifier", "build_notifiers", "register", "send_all"]
