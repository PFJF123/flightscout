---
name: flights
description: Search flights and manage availability/price watches via Google Flights data, using the installed `flightscout` CLI. Use when the user wants to find fares, compare dates or airports, ask when a far-out trip opens for booking, or track a route for availability or a price drop.
---

# flights

You drive the `flightscout` command-line tool to research cash flight fares (Google Flights data via `fli`) and manage fare watches. Shell out to the installed `flightscout` binary. Add `--json` to any command and parse the result when you need structured output to reason over.

Cash fares only: no miles, award, or points. The data comes from Google Flights' unofficial endpoint, so it is rate-limited. Keep calls modest and do not loop tightly.

## Prerequisites

The `flightscout` command must be on PATH (`pip install "flightscout[cli]"`). If a call fails with "command not found," tell the user to install it. IATA airport codes are required (BOS, BCN, etc.); if the user gives a city, resolve it to the main airport code first or ask.

## Searching fares

- Specific date: `flightscout search ORIGIN DEST DATE`
- Round trip: add `--return RETURN_DATE`
- Cheapest dates in a window: `flightscout cheapest ORIGIN DEST --from START --to END` (add `--round --duration N` for round-trip pairs)
- Flex a few days: `flightscout flexible ORIGIN DEST DATE --window 3`
- Compare nearby airports: `flightscout compare BOS,PVD BCN,GRO DATE` (comma-separated origins and destinations)

Common options: `--class ECONOMY|PREMIUM_ECONOMY|BUSINESS|FIRST`, `--stops`, `--airlines AA,DL`, `--limit N`. Use `--json` and read `best` for the cheapest option plus a Google Flights booking URL.

## Booking-frontier ETA (when can the trip be booked?)

When a user asks "why can't I book yet?" or "when can I book my flight for DATE?", run:

```
flightscout frontier ORIGIN DEST --target DATE
```

It probes the live route, reports the current booking frontier (furthest bookable date), tells you whether the target is bookable now, and if not, estimates the calendar date it will open. This is slower than a single search because it probes several dates: run it once, not in a loop. If the target is not yet bookable, offer to set an availability watch.

## Managing watches

A watch tracks one route and date and fires once.

- Availability (fires when the date opens for booking):
  `flightscout watch add availability ORIGIN DEST DATE --label "note"`
- Price (fires when the cheapest fare drops to or below a threshold):
  `flightscout watch add price ORIGIN DEST DATE --threshold 450`
- List: `flightscout watch list`
- Check all now (read-only status): `flightscout watch check`
- Remove: `flightscout watch rm WATCH_ID` (get the id from `watch list`)

Notification delivery happens when `flightscout watch check --notify` runs on a schedule (typically cron), using notifiers from the user's config. A plain `watch check` only reports status and sends nothing. If the user wants real alerts, point them at `examples/config.example.toml` and suggest a cron entry running `flightscout watch check --notify`.

## Style

Summarize results plainly: route, price, airline, stops, and the booking link. When you set a watch, echo back the watch id so the user can remove it later. Do not fabricate fares or dates: if a command errors, report the error rather than guessing.
