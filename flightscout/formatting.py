"""Human-readable rendering (markdown / plain text), dependency-free.

The CLI may layer `rich` on top for color, but these functions keep the library
usable (and testable) without it, and feed the MCP server clean text.
"""
from __future__ import annotations

from .models import DateFare, SearchResult


def _fmt_price(p, cur="USD") -> str:
    return f"{p:.0f} {cur}" if isinstance(p, (int, float)) else "—"


def format_search(res: SearchResult, *, limit: int = 10) -> str:
    head = f"### {res.route} · {res.date}" + (f" ↔ {res.return_date}" if res.return_date else "")
    head += f" · {res.cabin}"
    if not res.bookable:
        return head + f"\n\n_Not bookable ({res.count} flights)._"
    rows = ["| Price | Stops | Duration | Airlines | Depart → Arrive |",
            "|------|------|---------|---------|----------------|"]
    for f in res.flights[:limit]:
        rows.append(
            f"| {_fmt_price(f.price, f.currency)} | {f.stops} | {f.duration_str or '—'} "
            f"| {', '.join(f.airlines) or '—'}"
            f"{' via ' + ', '.join(f.via) if f.via else ''} "
            f"| {f.depart or '—'} → {f.arrive or '—'} |"
        )
    tail = f"\n[Open in Google Flights]({res.book_url})" if res.book_url else ""
    return head + f" · {res.count} flights\n\n" + "\n".join(rows) + tail


def format_dates(rows: list[DateFare], *, title: str = "Cheapest dates") -> str:
    if not rows:
        return f"### {title}\n\n_No results._"
    cheapest = min((r for r in rows if r.price is not None), key=lambda r: r.price, default=None)
    out = [f"### {title}", "", "| Date | Price |", "|------|------|"]
    for r in rows:
        mark = " ⬅ cheapest" if cheapest and r.date == cheapest.date else ""
        out.append(f"| {r.date}{(' → ' + r.return_date) if r.return_date else ''} | {_fmt_price(r.price, r.currency)}{mark} |")
    return "\n".join(out)


def format_frontier(d: dict) -> str:
    if d.get("error"):
        return f"**{d['route']}** — {d['error']}"
    lines = [f"### Booking frontier · {d['route']} · {d.get('cabin','ECONOMY')}",
             f"- Furthest bookable date today: **{d['frontier']}** ({d['horizon_days']}-day horizon)",
             f"- As of {d['as_of']}"]
    t = d.get("target")
    if t:
        if t.get("bookable_now"):
            lines.append(f"- **{t['date']} is bookable now.**")
        else:
            lines.append(f"- **{t['date']}** opens in ~{t['days_past_frontier']} days, "
                         f"est. **{t['est_open_date']}** ({t.get('note','')})")
    return "\n".join(lines)
