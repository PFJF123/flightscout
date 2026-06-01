"""Lightweight data models for flight results.

Plain dataclasses with `.to_dict()` so results serialize cleanly for the CLI,
MCP server, and JSON output. Built from the `fli` JSON shape.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Leg:
    origin: str
    dest: str
    depart: str | None
    arrive: str | None
    airline: str | None
    airline_code: str | None
    flight_number: str | None
    duration_min: int | None

    @classmethod
    def from_fli(cls, leg: dict) -> "Leg":
        air = leg.get("airline") or {}
        return cls(
            origin=(leg.get("departure_airport") or {}).get("code"),
            dest=(leg.get("arrival_airport") or {}).get("code"),
            depart=leg.get("departure_time"),
            arrive=leg.get("arrival_time"),
            airline=air.get("name"),
            airline_code=air.get("code"),
            flight_number=leg.get("flight_number"),
            duration_min=leg.get("duration"),
        )


@dataclass
class Flight:
    price: float | None
    currency: str
    stops: int | None
    duration_min: int | None
    legs: list[Leg] = field(default_factory=list)

    @property
    def airlines(self) -> list[str]:
        out: list[str] = []
        for leg in self.legs:
            if leg.airline and leg.airline not in out:
                out.append(leg.airline)
        return out

    @property
    def via(self) -> list[str]:
        return [leg.dest for leg in self.legs[:-1]] if len(self.legs) > 1 else []

    @property
    def duration_str(self) -> str | None:
        d = self.duration_min
        return f"{d // 60}h{d % 60:02d}m" if d else None

    @property
    def depart(self) -> str | None:
        return self.legs[0].depart if self.legs else None

    @property
    def arrive(self) -> str | None:
        return self.legs[-1].arrive if self.legs else None

    @classmethod
    def from_fli(cls, f: dict) -> "Flight":
        return cls(
            price=f.get("price"),
            currency=f.get("currency", "USD"),
            stops=f.get("stops"),
            duration_min=f.get("duration"),
            legs=[Leg.from_fli(leg) for leg in f.get("legs", [])],
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(
            airlines=self.airlines,
            via=self.via,
            duration=self.duration_str,
            depart=self.depart,
            arrive=self.arrive,
        )
        return d


@dataclass
class DateFare:
    """One row from a cheapest-dates / flexible search."""
    date: str
    price: float | None
    currency: str = "USD"
    return_date: str | None = None

    @classmethod
    def from_fli(cls, row: dict) -> "DateFare":
        return cls(
            date=row.get("departure_date"),
            price=row.get("price"),
            currency=row.get("currency", "USD"),
            return_date=row.get("return_date"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchResult:
    route: str
    date: str
    cabin: str
    count: int
    flights: list[Flight] = field(default_factory=list)
    book_url: str | None = None
    return_date: str | None = None

    @property
    def bookable(self) -> bool:
        return self.count > 0

    @property
    def best(self) -> Flight | None:
        return self.flights[0] if self.flights else None

    def to_dict(self, limit: int | None = None) -> dict:
        flights = self.flights if limit is None else self.flights[:limit]
        return {
            "route": self.route,
            "date": self.date,
            "return_date": self.return_date,
            "cabin": self.cabin,
            "count": self.count,
            "bookable": self.bookable,
            "best": self.best.to_dict() if self.best else None,
            "flights": [f.to_dict() for f in flights],
            "book_url": self.book_url,
        }
