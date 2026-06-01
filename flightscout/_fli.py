"""Low-level `fli` CLI invocation: binary discovery, JSON runner, retries, caching.

flightscout wraps the `fli` CLI (PyPI `flights`, Google Flights data). This module
is the only place that shells out. It distinguishes a genuine error (raises
`FliError`) from a valid empty result (returns a dict with count 0), and applies a
short TTL cache so repeated identical queries within one run don't re-hit Google.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

_CACHE: dict[tuple, tuple[float, dict]] = {}
_CACHE_TTL = float(os.environ.get("FLIGHTSCOUT_CACHE_TTL", "300"))  # seconds


class FliError(RuntimeError):
    """A flight query failed (fli missing, rate-limited, or unparseable)."""


def fli_bin() -> str | None:
    for cand in (
        os.environ.get("FLI_BIN"),
        shutil.which("fli"),
        os.path.expanduser("~/.local/bin/fli"),
        os.path.expanduser("~/.flights-venv/bin/fli"),
    ):
        if cand and os.path.exists(cand):
            return cand
    return None


def run_fli(args: list[str], *, retries: int = 2, timeout: int = 120, use_cache: bool = True) -> dict:
    """Run `fli <args> --format json` and return the parsed dict.

    Raises FliError on a hard failure (missing binary, rate-limit, bad output).
    A valid response with ``count: 0`` is returned normally, not treated as an error.
    """
    key = tuple(args)
    if use_cache and key in _CACHE:
        ts, val = _CACHE[key]
        if time.monotonic() - ts < _CACHE_TTL:
            return val

    binpath = fli_bin()
    if not binpath:
        raise FliError("fli not found — install with `pip install flights` (or `pipx install flights`)")

    cmd = [binpath] + args + ["--format", "json"]
    last_err = ""
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "").strip()
        if out:
            try:
                d = json.loads(out)
            except json.JSONDecodeError:
                last_err = out[:300]
            else:
                if isinstance(d, dict):
                    if use_cache:
                        _CACHE[key] = (time.monotonic(), d)
                    return d
                last_err = f"unexpected JSON type {type(d).__name__}"
        err = (proc.stderr or "").strip()
        if "429" in err or "429" in last_err or "rate" in err.lower():
            last_err = "rate-limited (429) by Google Flights"
        else:
            last_err = err or last_err or "empty response"
        if attempt < retries:
            time.sleep(3 * (attempt + 1))
    raise FliError(f"fli failed: {last_err}")


def clear_cache() -> None:
    _CACHE.clear()
