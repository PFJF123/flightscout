"""Core flight search over `fli`.

Adds the research-grade capabilities `fli` doesn't bundle: round-trip, flexible
dates, and multi-airport fan-out, plus a uniform options surface (cabin, stops,
airlines, alliance, layover, bags, emissions).

All functions return typed models from `flightscout.models`.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta

from ._fli import run_fli
from .models import DateFare, Flight, SearchResult


def book_url(origin: str, dest: str, date: str, return_date: str | None = None) -> str:
    trip = f"from {origin} to {dest} on {date}"
    if return_date:
        trip += f" returning {return_date}"
    else:
        trip += " one way"
    return "https://www.google.com/travel/flights?q=" + urllib.parse.quote(f"Flights {trip}")


def _opts(
    *,
    cabin: str | None = None,
    stops: str | None = None,
    airlines: str | None = None,
    sort: str | None = None,
    alliance: str | None = None,
    max_layover: int | None = None,
    min_layover: int | None = None,
    bags: int | None = None,
    exclude_basic: bool = False,
) -> list[str]:
    args: list[str] = []
    if cabin:
        args += ["--class", cabin]
    if stops:
        args += ["--stops", stops]
    if airlines:
        args += ["--airlines", airlines]
    if sort:
        args += ["--sort", sort]
    if alliance:
        args += ["--alliance", alliance]
    if max_layover is not None:
        args += ["--max-layover", str(max_layover)]
    if min_layover is not None:
        args += ["--min-layover", str(min_layover)]
    if bags is not None:
        args += ["--bags", str(bags)]
    if exclude_basic:
        args += ["--exclude-basic"]
    return args


def search(origin: str, dest: str, date: str, *, return_date: str | None = None, limit: int = 20, **opts) -> SearchResult:
    """One-way (or round-trip if `return_date` given) search on a specific date."""
    cabin = opts.get("cabin") or "ECONOMY"
    args = ["flights", origin, dest, date]
    if return_date:
        args += ["--return", return_date]
    args += _opts(**opts)
    d = run_fli(args)
    flights = [Flight.from_fli(f) for f in d.get("flights", [])]
    return SearchResult(
        route=f"{origin}->{dest}",
        date=date,
        return_date=return_date,
        cabin=cabin,
        count=d.get("count", len(flights)),
        flights=flights[:limit] if limit else flights,
        book_url=book_url(origin, dest, date, return_date),
    )


def cheapest_dates(
    origin: str, dest: str, date_from: str, date_to: str, *,
    duration: int | None = None, round_trip: bool = False, limit: int = 20, **opts,
) -> list[DateFare]:
    """Cheapest departure dates across a window (optionally round-trip with trip `duration`)."""
    args = ["dates", origin, dest, "--from", date_from, "--to", date_to]
    if duration is not None:
        args += ["--duration", str(duration)]
    if round_trip:
        args += ["--round"]
    if opts.get("cabin"):
        args += ["--class", opts["cabin"]]
    if opts.get("stops"):
        args += ["--stops", opts["stops"]]
    if opts.get("airlines"):
        args += ["--airlines", opts["airlines"]]
    d = run_fli(args)
    rows = d.get("dates")
    if rows is None:
        from ._fli import FliError
        raise FliError(f"unexpected `fli dates` shape, keys={list(d.keys())}")
    return [DateFare.from_fli(r) for r in rows[:limit]]


def flexible(origin: str, dest: str, date: str, *, window: int = 3, **opts) -> list[DateFare]:
    """Cheapest fare within +/- `window` days of `date` (one row per day)."""
    center = datetime.strptime(date, "%Y-%m-%d").date()
    start = (center - timedelta(days=window)).isoformat()
    end = (center + timedelta(days=window)).isoformat()
    return cheapest_dates(origin, dest, start, end, limit=2 * window + 1, **opts)


def multi_airport(origins: list[str], dests: list[str], date: str, *, limit: int = 20, **opts) -> SearchResult:
    """Fan out across origin/destination airport options, merge, and sort by price.

    e.g. multi_airport(["BOS","PVD"], ["BCN"], "2026-10-09") to compare nearby airports.
    """
    merged: list[Flight] = []
    pairs = [(o, d) for o in origins for d in dests]
    for o, d in pairs:
        try:
            res = search(o, d, date, limit=limit, **opts)
        except Exception:
            continue
        merged.extend(res.flights)
    merged.sort(key=lambda f: (f.price is None, f.price or 0))
    label = f"{'/'.join(origins)}->{'/'.join(dests)}"
    return SearchResult(
        route=label, date=date, cabin=opts.get("cabin") or "ECONOMY",
        count=len(merged), flights=merged[:limit],
        book_url=book_url(origins[0], dests[0], date),
    )
