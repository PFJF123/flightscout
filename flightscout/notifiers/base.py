"""Notifier interface, registry, and a shared HTTP helper.

A Notifier turns a (subject, html, text) message into a delivery. Implementations
register themselves with `@register("name")`, take their config dict in `__init__`
(validating there, raising ValueError if unusable), and `send()` raises on failure
so the watch loop can record the error and retry. Keep them stdlib-only.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from typing import Callable

# name -> factory(config_dict) -> Notifier  (a Notifier subclass is itself the factory)
_REGISTRY: dict[str, Callable[[dict], "Notifier"]] = {}


def register(name: str):
    def deco(factory):
        _REGISTRY[name] = factory
        return factory
    return deco


class Notifier:
    name = "base"

    def send(self, subject: str, html: str, text: str) -> None:
        raise NotImplementedError


def post(url: str, data: bytes, *, headers: dict | None = None, method: str = "POST", timeout: int = 30) -> None:
    """POST `data` to `url`; raise RuntimeError on a transport error or >=300 status."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"{url} returned HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{url} returned HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"{url} unreachable: {e.reason}")


def build_notifiers(notifiers_cfg: dict) -> list[Notifier]:
    """Instantiate every configured + registered notifier. Skips unknown/misconfigured
    ones with a warning rather than failing the whole run."""
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
    """Best-effort fan-out. Returns {name: True | error_str}. Raises only when every
    configured notifier fails. An empty list returns {} (delivered to nobody) — callers
    must treat that as 'not delivered'."""
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
