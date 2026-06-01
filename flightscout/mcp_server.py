"""MCP server for flightscout — flight research + fare-watch over Google Flights data.

Exposes the flightscout toolkit to MCP-capable agents over stdio: round-trip and
flexible search, cheapest-date scanning, the booking-frontier "when does my date
open for booking?" tool, and CRUD over availability/price watches.

Run as the `flightscout-mcp` entry point, or directly:  python -m flightscout.mcp_server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

import flightscout

mcp = FastMCP("flightscout")


def _opts(**kwargs) -> dict:
    """Build a kwargs dict for flightscout search functions, omitting any None values
    so unset optional filters don't get passed through to the `fli` CLI surface."""
    return {k: v for k, v in kwargs.items() if v is not None}


@mcp.tool()
def search_flights(
    origin: str,
    dest: str,
    date: str,
    return_date: str | None = None,
    cabin: str = "ECONOMY",
    stops: str = "ANY",
    airlines: str | None = None,
    limit: int = 10,
) -> dict:
    """Search live cash fares for a specific date (one-way, or round-trip if `return_date` is set).

    Use this when the traveler already knows the exact date(s) and wants the actual
    flight list with prices, airlines, stops, and times.

    Args:
        origin: Origin airport IATA code, e.g. "BOS".
        dest: Destination airport IATA code, e.g. "BCN".
        date: Departure date, "YYYY-MM-DD".
        return_date: Optional return date for a round trip, "YYYY-MM-DD".
        cabin: Cabin class — ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST.
        stops: Stop filter — ANY, NON_STOP, ONE_STOP, or TWO_PLUS_STOPS.
        airlines: Optional comma-separated airline codes to restrict to, e.g. "AA,DL".
        limit: Max number of flights to return.

    Returns a result dict with the route, the best (cheapest) flight, the flight list,
    and a Google Flights booking URL.
    """
    try:
        opts = _opts(
            return_date=return_date, cabin=cabin, stops=stops, airlines=airlines
        )
        return flightscout.search(origin, dest, date, **opts).to_dict(limit=limit)
    except flightscout.FliError as e:
        return {"error": str(e)}


@mcp.tool()
def cheapest_dates(
    origin: str,
    dest: str,
    date_from: str,
    date_to: str,
    cabin: str = "ECONOMY",
    round_trip: bool = False,
    duration: int | None = None,
    limit: int = 20,
) -> dict:
    """Find the cheapest departure dates across a date range for a route.

    Use this when the traveler is flexible on when to fly and wants to know which
    dates in a window are cheapest. For round trips, pass round_trip=True and a trip
    `duration` (nights) to price the cheapest outbound/return pairs.

    Args:
        origin: Origin airport IATA code.
        dest: Destination airport IATA code.
        date_from: Earliest departure date to consider, "YYYY-MM-DD".
        date_to: Latest departure date to consider, "YYYY-MM-DD".
        cabin: Cabin class — ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST.
        round_trip: If True, price round trips (requires `duration`).
        duration: Trip length in nights for round-trip pricing.
        limit: Max number of date rows to return.

    Returns {"results": [...]} sorted cheapest-first, one row per date.
    """
    try:
        opts = _opts(
            cabin=cabin, round_trip=round_trip, duration=duration, limit=limit
        )
        rows = flightscout.cheapest_dates(origin, dest, date_from, date_to, **opts)
        return {"results": [d.to_dict() for d in rows]}
    except flightscout.FliError as e:
        return {"error": str(e)}


@mcp.tool()
def flexible_dates(
    origin: str,
    dest: str,
    date: str,
    window: int = 3,
    cabin: str = "ECONOMY",
) -> dict:
    """Price the cheapest fare for each day within +/- `window` days of a target date.

    Use this when the traveler has a date in mind but could shift a few days to save —
    it returns one row per day around the date so you can compare.

    Args:
        origin: Origin airport IATA code.
        dest: Destination airport IATA code.
        date: Target departure date, "YYYY-MM-DD".
        window: Number of days to scan on each side of the target date.
        cabin: Cabin class — ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST.

    Returns {"results": [...]}, one row per day in the window.
    """
    try:
        opts = _opts(window=window, cabin=cabin)
        rows = flightscout.flexible(origin, dest, date, **opts)
        return {"results": [d.to_dict() for d in rows]}
    except flightscout.FliError as e:
        return {"error": str(e)}


@mcp.tool()
def booking_frontier(
    origin: str,
    dest: str,
    target: str | None = None,
    cabin: str = "ECONOMY",
) -> dict:
    """Find out WHEN a future date opens for booking — the booking-frontier tool.

    This is flightscout's differentiator. Airlines only sell on a rolling horizon
    (commonly ~330-360 days out), so a date further out simply isn't bookable yet.
    This tool binary-searches the furthest-out bookable date for the route (the
    "frontier"), and if you pass a `target` date beyond it, estimates the calendar
    date on which that target will open for booking. Use it whenever someone asks
    "why can't I book yet?" or "when can I book my flight for <date>?".

    Args:
        origin: Origin airport IATA code.
        dest: Destination airport IATA code.
        target: Optional future date you want to book, "YYYY-MM-DD". If given and it
            is past the frontier, the result includes an estimated open date.
        cabin: Cabin class — ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST.

    Returns the current frontier date, horizon in days, and (if `target` set) whether
    it is bookable now plus an estimated open date. Note: this probes the live endpoint
    across several dates and is slower than a single search.
    """
    try:
        opts = _opts(target=target, cabin=cabin)
        return flightscout.frontier(origin, dest, **opts)
    except flightscout.FliError as e:
        return {"error": str(e)}


@mcp.tool()
def list_watches() -> dict:
    """List all configured fare watches (availability and price), with their settings.

    Use this to see what the traveler is currently tracking before adding or removing
    a watch. Returns {"watches": [...]}.
    """
    try:
        return {"watches": flightscout.list_watches()}
    except flightscout.FliError as e:
        return {"error": str(e)}


@mcp.tool()
def add_watch(
    type: str,
    origin: str,
    dest: str,
    date: str,
    cabin: str = "ECONOMY",
    stops: str = "ANY",
    threshold: float | None = None,
    label: str = "",
) -> dict:
    """Create a fare watch that fires once when a route becomes bookable or drops in price.

    Use this when the traveler wants to be alerted about a future trip. An
    "availability" watch fires when the date opens for booking (pairs naturally with
    booking_frontier for dates not yet on sale). A "price" watch fires when the
    cheapest fare drops to at or below `threshold`.

    Args:
        type: Watch type — "availability" or "price".
        origin: Origin airport IATA code.
        dest: Destination airport IATA code.
        date: Departure date to watch, "YYYY-MM-DD".
        cabin: Cabin class — ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST.
        stops: Stop filter — ANY, NON_STOP, ONE_STOP, or TWO_PLUS_STOPS.
        threshold: Required for a "price" watch — the price at or below which to fire.
        label: Optional human-readable note attached to the watch.

    Returns {"added": <watch>} with the created watch definition.
    """
    try:
        return {
            "added": flightscout.add_watch(
                type, origin, dest, date,
                cabin=cabin, stops=stops, threshold=threshold, label=label,
            )
        }
    except (flightscout.FliError, ValueError) as e:
        return {"error": str(e)}


@mcp.tool()
def remove_watch(id: str) -> dict:
    """Delete a fare watch by its id.

    Use this to stop tracking a route. Get the id from list_watches first.
    Returns {"removed": true} if a watch was deleted, or {"removed": false} if no
    watch with that id exists.

    Args:
        id: The watch id to remove.
    """
    try:
        return {"removed": flightscout.remove_watch(id)}
    except flightscout.FliError as e:
        return {"error": str(e)}


@mcp.tool()
def check_watches() -> dict:
    """Evaluate every active watch now and report which would fire — read-only.

    Use this to get the current status of all watches on demand. This does NOT send
    any notifications (email/ntfy/etc.); it only reports. Notification delivery is
    handled by the scheduled CLI run, not by this tool.

    Returns a report dict: how many were checked, which fired, and per-watch results.
    """
    try:
        # Truly read-only: no notifications, no history write, no state persistence.
        return flightscout.check_watches(notify=False, record_history=False, persist=False)
    except flightscout.FliError as e:
        return {"error": str(e)}


def main() -> None:
    """Run the flightscout MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
