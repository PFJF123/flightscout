"""Typer CLI for flightscout.

Thin command layer over the library: search / cheapest / flexible / compare /
frontier, plus watch management and fare history. Every command takes `--json`
to emit the raw dict instead of a rich table; otherwise we render rich tables
where sensible and fall back to the `formatting.*` markdown for the rest.
"""
from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from . import (
    FliError,
    add_watch as _add_watch,
    cheapest_dates,
    check_watches,
    flexible as _flexible,
    frontier as _frontier,
    history,
    list_watches,
    multi_airport,
    remove_watch,
    search,
)
from . import formatting

app = typer.Typer(add_completion=False, help="Research flights and know when to book.")
watch_app = typer.Typer(help="Manage availability/price watches.")
app.add_typer(watch_app, name="watch")

console = Console()


# ---------------------------------------------------------------- helpers
def _print(obj, as_json: bool) -> None:
    """Render a dict/str: JSON dump when asked, else markdown via rich."""
    if as_json:
        payload = obj if not hasattr(obj, "to_dict") else obj.to_dict()
        console.print_json(_json.dumps(payload, default=str))
    else:
        console.print(Markdown(obj if isinstance(obj, str) else str(obj)))


def _opts(**kw) -> dict:
    """Drop None/empty values so we only pass provided filters to the library."""
    return {k: v for k, v in kw.items() if v is not None}


def _fail(e: Exception) -> None:
    console.print(f"[bold red]Error:[/] {e}")
    raise typer.Exit(1)


# ---------------------------------------------------------------- search
@app.command("search")
def search_cmd(
    origin: str = typer.Argument(..., metavar="ORIGIN"),
    dest: str = typer.Argument(..., metavar="DEST"),
    date: str = typer.Argument(..., metavar="DATE"),
    return_: Optional[str] = typer.Option(None, "--return", help="Return date for round-trip."),
    cabin: str = typer.Option("ECONOMY", "--class", help="Cabin class."),
    stops: Optional[str] = typer.Option(None, "--stops"),
    airlines: Optional[str] = typer.Option(None, "--airlines"),
    alliance: Optional[str] = typer.Option(None, "--alliance"),
    max_layover: Optional[int] = typer.Option(None, "--max-layover"),
    bags: Optional[int] = typer.Option(None, "--bags"),
    exclude_basic: bool = typer.Option(False, "--exclude-basic"),
    sort: Optional[str] = typer.Option(None, "--sort"),
    limit: int = typer.Option(20, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Search a specific date (round-trip if --return given)."""
    opts = _opts(
        cabin=cabin, stops=stops, airlines=airlines, alliance=alliance,
        max_layover=max_layover, bags=bags,
        exclude_basic=exclude_basic or None, sort=sort,
    )
    try:
        res = search(origin, dest, date, return_date=return_, limit=limit, **opts)
    except FliError as e:
        _fail(e)
    if as_json:
        _print(res.to_dict(), True)
    else:
        console.print(Markdown(formatting.format_search(res, limit=limit)))


# ---------------------------------------------------------------- cheapest
@app.command()
def cheapest(
    origin: str = typer.Argument(..., metavar="ORIGIN"),
    dest: str = typer.Argument(..., metavar="DEST"),
    date_from: str = typer.Option(..., "--from", help="Window start (YYYY-MM-DD)."),
    date_to: str = typer.Option(..., "--to", help="Window end (YYYY-MM-DD)."),
    duration: Optional[int] = typer.Option(None, "--duration", help="Round-trip length in days."),
    round_trip: bool = typer.Option(False, "--round"),
    cabin: str = typer.Option("ECONOMY", "--class"),
    stops: Optional[str] = typer.Option(None, "--stops"),
    airlines: Optional[str] = typer.Option(None, "--airlines"),
    limit: int = typer.Option(20, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Cheapest departure dates across a window."""
    opts = _opts(cabin=cabin, stops=stops, airlines=airlines)
    try:
        rows = cheapest_dates(
            origin, dest, date_from, date_to,
            duration=duration, round_trip=round_trip, limit=limit, **opts,
        )
    except FliError as e:
        _fail(e)
    if as_json:
        _print([r.to_dict() for r in rows], True)
    else:
        title = f"Cheapest dates · {origin}->{dest}"
        console.print(Markdown(formatting.format_dates(rows, title=title)))


# ---------------------------------------------------------------- flexible
@app.command()
def flexible(
    origin: str = typer.Argument(..., metavar="ORIGIN"),
    dest: str = typer.Argument(..., metavar="DEST"),
    date: str = typer.Argument(..., metavar="DATE"),
    window: int = typer.Option(3, "--window", help="+/- days around DATE."),
    cabin: str = typer.Option("ECONOMY", "--class"),
    stops: Optional[str] = typer.Option(None, "--stops"),
    airlines: Optional[str] = typer.Option(None, "--airlines"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Cheapest fare within +/- window days of DATE."""
    opts = _opts(cabin=cabin, stops=stops, airlines=airlines)
    try:
        rows = _flexible(origin, dest, date, window=window, **opts)
    except FliError as e:
        _fail(e)
    if as_json:
        _print([r.to_dict() for r in rows], True)
    else:
        title = f"Flexible · {origin}->{dest} · {date} ±{window}d"
        console.print(Markdown(formatting.format_dates(rows, title=title)))


# ---------------------------------------------------------------- compare
@app.command()
def compare(
    origins: str = typer.Argument(..., metavar="ORIGINS", help="Comma-separated origins."),
    dests: str = typer.Argument(..., metavar="DESTS", help="Comma-separated destinations."),
    date: str = typer.Argument(..., metavar="DATE"),
    cabin: str = typer.Option("ECONOMY", "--class"),
    limit: int = typer.Option(20, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Fan out across nearby airports and merge by price."""
    o = [x.strip() for x in origins.split(",") if x.strip()]
    d = [x.strip() for x in dests.split(",") if x.strip()]
    try:
        res = multi_airport(o, d, date, limit=limit, cabin=cabin)
    except FliError as e:
        _fail(e)
    if as_json:
        _print(res.to_dict(), True)
    else:
        console.print(Markdown(formatting.format_search(res, limit=limit)))


# ---------------------------------------------------------------- frontier
@app.command()
def frontier(
    origin: str = typer.Argument(..., metavar="ORIGIN"),
    dest: str = typer.Argument(..., metavar="DEST"),
    target: Optional[str] = typer.Option(None, "--target", help="Date to test for booking openness."),
    cabin: str = typer.Option("ECONOMY", "--class"),
    as_json: bool = typer.Option(False, "--json"),
):
    """When does a route's booking window open out to a target date?"""
    try:
        d = _frontier(origin, dest, target=target, cabin=cabin)
    except FliError as e:
        _fail(e)
    if as_json:
        _print(d, True)
    else:
        console.print(Markdown(formatting.format_frontier(d)))


# ---------------------------------------------------------------- watch
@watch_app.command("add")
def watch_add(
    wtype: str = typer.Argument(..., metavar="availability|price"),
    origin: str = typer.Argument(..., metavar="ORIGIN"),
    dest: str = typer.Argument(..., metavar="DEST"),
    date: str = typer.Argument(..., metavar="DATE"),
    cabin: str = typer.Option("ECONOMY", "--class"),
    stops: str = typer.Option("ANY", "--stops"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="Price watch trigger."),
    label: str = typer.Option("", "--label"),
):
    """Add an availability or price watch."""
    try:
        w = _add_watch(wtype, origin, dest, date, cabin=cabin, stops=stops,
                       threshold=threshold, label=label)
    except (ValueError, FliError) as e:
        _fail(e)
    console.print(f"[green]Added watch[/] [bold]{w['id']}[/]")


@watch_app.command("list")
def watch_list(as_json: bool = typer.Option(False, "--json")):
    """List configured watches."""
    watches = list_watches()
    if as_json:
        _print(watches, True)
        return
    if not watches:
        console.print("_No watches configured._")
        return
    t = Table(title="Watches")
    for col in ("ID", "Type", "Route", "Date", "Class", "Stops", "Threshold", "Label"):
        t.add_column(col)
    for w in watches:
        t.add_row(
            w.get("id", ""), w.get("type", ""),
            f"{w.get('origin', '')}->{w.get('dest', '')}", w.get("date", ""),
            w.get("cabin", ""), w.get("stops", ""),
            "" if w.get("threshold") is None else str(w["threshold"]),
            w.get("label", ""),
        )
    console.print(t)


@watch_app.command("rm")
def watch_rm(watch_id: str = typer.Argument(..., metavar="ID")):
    """Remove a watch by id."""
    if remove_watch(watch_id):
        console.print(f"[green]Removed[/] {watch_id}")
    else:
        console.print(f"[yellow]No such watch:[/] {watch_id}")
        raise typer.Exit(1)


@watch_app.command("check")
def watch_check(
    notify: bool = typer.Option(False, "--notify", help="Send alerts via configured notifiers."),
    as_json: bool = typer.Option(False, "--json"),
):
    """Evaluate every active watch (cron entrypoint)."""
    from .config import load_config
    from .notifiers import build_notifiers

    ns = build_notifiers(load_config().get("notifiers", {}))
    try:
        report = check_watches(ns, notify=notify)
    except FliError as e:
        _fail(e)
    if as_json:
        _print(report, True)
        return
    fired = report.get("fired", [])
    console.print(f"Checked [bold]{report.get('checked', 0)}[/] watches · "
                  f"fired [bold]{len(fired)}[/]"
                  + (f" → {', '.join(fired)}" if fired else ""))
    t = Table(title="Watch check")
    for col in ("ID", "Status", "Fired", "Count", "Signal"):
        t.add_column(col)
    for r in report.get("results", []):
        t.add_row(
            r.get("id", ""), r.get("status", ""),
            "✓" if r.get("fired") else "", str(r.get("count", "")),
            r.get("signal", ""),
        )
    console.print(t)


# ---------------------------------------------------------------- history
@app.command("history")
def history_cmd(
    watch_id: str = typer.Argument(..., metavar="ID"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Show fare history and the book-now signal for a watch."""
    series = history.series(watch_id)
    current = series[-1]["price"] if series else None
    sig = history.signal(watch_id, current)
    if as_json:
        _print({"id": watch_id, "series": series, "signal": sig}, True)
        return
    if not series:
        console.print(f"_No history for {watch_id}._")
        return
    t = Table(title=f"Fare history · {watch_id}")
    t.add_column("Date")
    t.add_column("Price", justify="right")
    for p in series:
        t.add_row(p.get("date", ""), str(p.get("price", "")))
    console.print(t)
    if sig:
        console.print(f"Signal: [bold]{sig['verdict']}[/] · current {sig['current']} "
                      f"vs 30-day median {sig['median']} "
                      f"({sig['vs_median_pct']:+}%, n={sig['samples']})")
    else:
        console.print("_Not enough history for a signal (need 3+ points)._")


if __name__ == "__main__":
    app()
