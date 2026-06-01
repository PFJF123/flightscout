"""Configuration: paths and notifier setup, from a TOML file and/or env vars.

Zero personal data ships in the package. Resolution order for the config file:
  1. $FLIGHTSCOUT_CONFIG
  2. ./flightscout.toml
  3. ~/.config/flightscout/config.toml

Watch definitions and runtime state live under a data dir ($FLIGHTSCOUT_HOME or
~/.flightscout), so multiple machines keep independent fired-state.
"""
from __future__ import annotations

import os

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


def data_home() -> str:
    return os.path.expanduser(os.environ.get("FLIGHTSCOUT_HOME", "~/.flightscout"))


def watches_path() -> str:
    return os.path.join(data_home(), "watches.json")


def state_path() -> str:
    return os.path.join(data_home(), "state.json")


def history_path() -> str:
    return os.path.join(data_home(), "history.json")


def _config_file() -> str | None:
    for cand in (
        os.environ.get("FLIGHTSCOUT_CONFIG"),
        "flightscout.toml",
        os.path.expanduser("~/.config/flightscout/config.toml"),
    ):
        if cand and os.path.exists(cand):
            return cand
    return None


def load_config() -> dict:
    """Return the merged config dict. Env vars override file values for notifiers."""
    cfg: dict = {"notifiers": {}}
    path = _config_file()
    if path and tomllib:
        with open(path, "rb") as fh:
            cfg.update(tomllib.load(fh))
    cfg.setdefault("notifiers", {})
    _apply_env_notifiers(cfg["notifiers"])
    return cfg


def _apply_env_notifiers(n: dict) -> None:
    """Let env vars configure notifiers without a config file (12-factor friendly)."""
    env = os.environ
    if env.get("FLIGHTSCOUT_NTFY_TOPIC"):
        n.setdefault("ntfy", {})["topic"] = env["FLIGHTSCOUT_NTFY_TOPIC"]
        if env.get("FLIGHTSCOUT_NTFY_SERVER"):
            n["ntfy"]["server"] = env["FLIGHTSCOUT_NTFY_SERVER"]
    if env.get("FLIGHTSCOUT_TELEGRAM_TOKEN") and env.get("FLIGHTSCOUT_TELEGRAM_CHAT_ID"):
        n["telegram"] = {"token": env["FLIGHTSCOUT_TELEGRAM_TOKEN"], "chat_id": env["FLIGHTSCOUT_TELEGRAM_CHAT_ID"]}
    if env.get("FLIGHTSCOUT_DISCORD_WEBHOOK"):
        n["discord"] = {"webhook_url": env["FLIGHTSCOUT_DISCORD_WEBHOOK"]}
    if env.get("FLIGHTSCOUT_WEBHOOK_URL"):
        n["webhook"] = {"url": env["FLIGHTSCOUT_WEBHOOK_URL"]}
    if env.get("FLIGHTSCOUT_SMTP_HOST"):
        n["email"] = {
            "host": env["FLIGHTSCOUT_SMTP_HOST"],
            "port": int(env.get("FLIGHTSCOUT_SMTP_PORT", "587")),
            "username": env.get("FLIGHTSCOUT_SMTP_USER", ""),
            "password": env.get("FLIGHTSCOUT_SMTP_PASS", ""),
            "from_addr": env.get("FLIGHTSCOUT_SMTP_FROM", env.get("FLIGHTSCOUT_SMTP_USER", "")),
            "to_addr": env.get("FLIGHTSCOUT_SMTP_TO", ""),
        }
