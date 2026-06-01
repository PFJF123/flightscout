"""Crash-safe JSON stores for watch definitions and runtime state.

Writes are atomic (temp file + os.replace) and reads are tolerant: a corrupt or
truncated state file must never brick the daily watch run, so it falls back to {}.
"""
from __future__ import annotations

import json
import os
import sys


def _atomic_write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path) as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        print(f"warning: {path} unreadable ({e}); using default", file=sys.stderr)
        return default


def save_json(path: str, obj) -> None:
    _atomic_write(path, json.dumps(obj, indent=2) + "\n")
