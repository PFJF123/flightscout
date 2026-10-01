"""Tests for the low-level fli subprocess wrapper."""
from __future__ import annotations

import json
import subprocess

import pytest

import flightscout._fli as fli_mod
from flightscout._fli import FliError


@pytest.fixture(autouse=True)
def _mock_binary_and_sleep(monkeypatch):
    fli_mod.clear_cache()
    monkeypatch.setattr(fli_mod, "fli_bin", lambda: "/tmp/fli")
    monkeypatch.setattr(fli_mod.time, "sleep", lambda _seconds: None)


def test_structured_failure_raises_and_is_not_cached(monkeypatch):
    calls = []
    responses = [
        subprocess.CompletedProcess([], 1, json.dumps({"success": False, "error": "rate limited"}), ""),
        subprocess.CompletedProcess([], 0, json.dumps({"success": True, "count": 0, "flights": []}), ""),
    ]

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(fli_mod.subprocess, "run", fake_run)
    args = ["flights", "BOS", "BCN", "2026-10-09"]
    with pytest.raises(FliError, match="rate-limited"):
        fli_mod.run_fli(args, retries=0)
    result = fli_mod.run_fli(args, retries=0)

    assert result["success"] is True
    assert len(calls) == 2


def test_timeout_is_retried_then_raised_as_fli_error(monkeypatch):
    calls = []

    def timeout(*args, **kwargs):
        calls.append((args, kwargs))
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(fli_mod.subprocess, "run", timeout)
    with pytest.raises(FliError, match="timed out"):
        fli_mod.run_fli(["flights", "BOS", "BCN", "2026-10-09"], retries=2)

    assert len(calls) == 3
