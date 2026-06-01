"""Booking-frontier intelligence: "when does my date open for booking?"

Airlines sell on a rolling horizon (commonly ~330-360 days). This binary-searches
the furthest-out bookable date for a route, then estimates when a target date will
open (the window advances ~1 day per day).

Assumes availability is roughly monotonic (a clean cliff on busy routes); on a
sparse route with mid-range gaps the frontier can land short. Errors are NOT treated
as "empty" — a rate-limit aborts with a partial answer rather than reporting a wrong,
too-early date.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from ._fli import FliError, run_fli
from .search import _opts


def _count_on(origin: str, dest: str, d: str, opts: list[str]) -> int | None:
    """Count for a date, or None on error (distinct from 0 = no availability)."""
    try:
        return run_fli(["flights", origin, dest, d] + opts).get("count", 0)
    except FliError:
        return None


def frontier(origin: str, dest: str, *, target: str | None = None, sleep: float = 2.0, **opts) -> dict:
    flags = _opts(**opts)
    today = date.today()
    lo = today + timedelta(days=1)     # assumed bookable
    hi = today + timedelta(days=400)   # assumed beyond horizon

    near = _count_on(origin, dest, lo.isoformat(), flags)
    if near is None:
        return {"route": f"{origin}->{dest}", "error": "rate-limited on near-term probe; try again"}
    if near <= 0:
        return {"route": f"{origin}->{dest}", "error": "no near-term availability — check the route"}

    while (hi - lo).days > 1:
        mid = lo + timedelta(days=(hi - lo).days // 2)
        time.sleep(sleep)
        c = _count_on(origin, dest, mid.isoformat(), flags)
        if c is None:
            time.sleep(sleep + 3)
            c = _count_on(origin, dest, mid.isoformat(), flags)
        if c is None:
            return {
                "route": f"{origin}->{dest}",
                "error": "rate-limited mid-search; frontier is at least " + lo.isoformat(),
                "frontier_at_least": lo.isoformat(),
            }
        if c > 0:
            lo = mid
        else:
            hi = mid

    out = {
        "route": f"{origin}->{dest}",
        "cabin": opts.get("cabin") or "ECONOMY",
        "frontier": lo.isoformat(),
        "horizon_days": (lo - today).days,
        "as_of": today.isoformat(),
    }
    if target:
        tgt = datetime.strptime(target, "%Y-%m-%d").date()
        if tgt <= lo:
            out["target"] = {"date": target, "bookable_now": True}
        else:
            days_out = (tgt - lo).days
            out["target"] = {
                "date": target,
                "bookable_now": False,
                "days_past_frontier": days_out,
                "est_open_date": (today + timedelta(days=days_out)).isoformat(),
                "note": "estimate; airlines load schedules in batches, so actual open may differ by a few days",
            }
    return out
