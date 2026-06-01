# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-01

Initial release.

### Added
- Flight search over `fli` (Google Flights data): specific-date `search`,
  round-trip search, `cheapest` dates across a window, `flexible` +/- day
  search, and multi-airport `compare`.
- **Booking-frontier** tool: finds the furthest bookable date for a route and
  estimates when a future target date will open for booking.
- **Watches**: availability and price watches with fire-once delivery,
  detection latched separately from notification (no lost alerts on a notifier
  outage), and a dead-man's-switch that warns when a watch keeps erroring.
- Six pluggable notifiers: console (zero-config default), email/SMTP, Telegram,
  Discord, ntfy, and a generic JSON webhook. Configurable via TOML or env vars.
- Fare history recording with a vs-30-day-median book-now signal.
- `flightscout` Typer + rich CLI, with `--json` on every command.
- `flightscout-mcp` MCP server exposing search, cheapest/flexible dates, the
  booking frontier, and watch CRUD as agent tools.
- Drop-in Claude skill at `skill/flights.md`.

[Unreleased]: https://github.com/PFJF123/flightscout/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/PFJF123/flightscout/releases/tag/v0.1.0
