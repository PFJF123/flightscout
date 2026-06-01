"""flightscout — research flights and know when to book.

A research + fare-watch toolkit on top of `fli` (Google Flights data): round-trip
and flexible search, multi-airport compare, a booking-frontier "when does my date
open?" tool, and reliable availability/price watches with pluggable alerts.

Cash fares only (no award/points availability). Uses Google Flights' unofficial
endpoint via `fli`; be a polite, low-volume citizen.
"""
from __future__ import annotations

from ._fli import FliError
from .frontier import frontier
from .models import DateFare, Flight, Leg, SearchResult
from .search import cheapest_dates, flexible, multi_airport, search
from .watch import add_watch, check_watches, list_watches, remove_watch

__version__ = "0.1.0"

__all__ = [
    "search", "cheapest_dates", "flexible", "multi_airport", "frontier",
    "add_watch", "list_watches", "remove_watch", "check_watches",
    "SearchResult", "Flight", "Leg", "DateFare", "FliError", "__version__",
]
