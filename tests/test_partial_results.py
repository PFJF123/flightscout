"""Exercise partial comparisons through library and CLI interfaces offline."""
from __future__ import annotations

import importlib
import json

import pytest
from typer.testing import CliRunner

from flightscout import FliError
from flightscout.cli import app
from flightscout.formatting import format_search

search_mod = importlib.import_module("flightscout.search")


def test_complete_comparison_keeps_sorted_fares_and_explicit_complete_status(monkeypatch):
    monkeypatch.setattr(search_mod, "run_fli", lambda args: {
        "count": 1, "flights": [{"price": {"BOS": 500, "PVD": 250}[args[1]]}]
    })
    result = search_mod.multi_airport(["BOS", "PVD"], ["BCN"], "2026-11-22")
    payload = result.to_dict()
    assert payload["incomplete"] is False
    assert payload["failed_pairs"] == []
    assert [flight.price for flight in result.flights] == [250, 500]
    assert "Incomplete comparison" not in format_search(result)


@pytest.fixture
def partial(monkeypatch):
    def fake(args):
        if args[1] == "BOS":
            raise FliError("rate-limited 429")
        return {"count": 1, "flights": [{"price": 250}]}

    monkeypatch.setattr(search_mod, "run_fli", fake)


def test_partial_comparison_cli_text_and_json(partial):
    args = ["compare", "BOS,PVD", "BCN", "2026-11-22"]
    runner = CliRunner()
    text = runner.invoke(app, args)
    assert text.exit_code == 0
    assert "Incomplete comparison" in text.stdout
    assert "BOS->BCN" in text.stdout
    assert "rate-limited 429" in text.stdout
    assert "250 USD" in text.stdout
    encoded = runner.invoke(app, args + ["--json"])
    assert encoded.exit_code == 0
    payload = json.loads(encoded.stdout)
    assert payload["incomplete"] is True
    assert payload["failed_pairs"] == [
        {"origin": "BOS", "dest": "BCN", "error": "rate-limited 429"}
    ]
    assert payload["best"]["price"] == 250


def test_all_pairs_failing_remains_an_error_with_each_pair_identified(monkeypatch):
    def fail(args):
        raise FliError("rate-limited 429")

    monkeypatch.setattr(search_mod, "run_fli", fail)
    with pytest.raises(FliError, match="all airport pairs failed") as raised:
        search_mod.multi_airport(["BOS", "PVD"], ["BCN"], "2026-11-22")
    assert "BOS->BCN: rate-limited 429" in str(raised.value)
    assert "PVD->BCN: rate-limited 429" in str(raised.value)


def test_empty_success_is_still_incomplete_if_another_pair_failed(monkeypatch):
    def fake(args):
        if args[1] == "BOS":
            raise FliError("rate-limited 429")
        return {"count": 0, "flights": []}

    monkeypatch.setattr(search_mod, "run_fli", fake)
    result = search_mod.multi_airport(["BOS", "PVD"], ["BCN"], "2026-11-22")
    assert result.incomplete is True
    assert result.bookable is False
    assert "Incomplete comparison" in format_search(result)
    assert "Not bookable" in format_search(result)
