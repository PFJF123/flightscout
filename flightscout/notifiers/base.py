"""Notifier interface and a small registry.

A Notifier turns a (subject, html, text) message into a delivery. Implementations
must be configured from a plain dict (from config.toml or env) and raise on failure
so the watch loop can record the error and retry. Keep them stdlib-only.
"""
from __future__ import annotations

from typing import Callable

# name -> factory(config_dict) -> Notifier
_REGISTRY: dict[str, Callable[[dict], "Notifier"]] = {}


def register(name: str):
    def deco(factory: Callable[[dict], "Notifier"]):
        _REGISTRY[name] = factory
        return factory
    return deco


class Notifier:
    """Base class. Subclasses implement `send`."""

    name = "base"

    def send(self, subject: str, html: str, text: str) -> None:
        raise NotImplementedError

    # Subclasses override to validate their config; raise ValueError if unusable.
    @classmethod
    def from_config(cls, cfg: dict) -> "Notifier":
        raise NotImplementedError


def build_notifiers(notifiers_cfg: dict) -> list[Notifier]:
    """Instantiate every configured + registered notifier. Skips unknown/misconfigured
    ones with a warning rather than failing the whole run."""
    import sys

    out: list[Notifier] = []
    for name, cfg in (notifiers_cfg or {}).items():
        factory = _REGISTRY.get(name)
        if not factory:
            print(f"warning: unknown notifier '{name}' (skipped)", file=sys.stderr)
            continue
        if isinstance(cfg, dict) and cfg.get("enabled") is False:
            continue
        try:
            out.append(factory(cfg if isinstance(cfg, dict) else {}))
        except Exception as e:  # noqa: BLE001
            print(f"warning: notifier '{name}' misconfigured ({e}); skipped", file=sys.stderr)
    return out


def send_all(notifiers: list[Notifier], subject: str, html: str, text: str) -> dict:
    """Best-effort fan-out. Returns {notifier_name: True | error_str}. Succeeds if
    at least one delivered; raises RuntimeError only if ALL configured notifiers fail."""
    results: dict[str, object] = {}
    any_ok = False
    for n in notifiers:
        try:
            n.send(subject, html, text)
            results[n.name] = True
            any_ok = True
        except Exception as e:  # noqa: BLE001
            results[n.name] = str(e)
    if notifiers and not any_ok:
        raise RuntimeError(f"all notifiers failed: {results}")
    return results
