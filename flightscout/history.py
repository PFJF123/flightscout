"""Fare-history logging and a simple "good time to book?" signal.

Each watch check appends the day's cheapest fare to history.json. From that we
derive whether the current price is below the recent median — the cheap, honest
version of a "book now?" hint (no predictions, just where today sits vs the trend).
"""
from __future__ import annotations

from datetime import date
from statistics import median

from . import config
from .state import load_json, save_json


def record(watch_id: str, price: float | None, *, on: str | None = None) -> None:
    if price is None:
        return
    path = config.history_path()
    hist = load_json(path, {})
    series = hist.setdefault(watch_id, [])
    day = on or date.today().isoformat()
    if series and series[-1].get("date") == day:
        series[-1]["price"] = price  # one point per day; keep the latest
    else:
        series.append({"date": day, "price": price})
    hist[watch_id] = series[-365:]  # cap a year
    save_json(path, hist)


def series(watch_id: str) -> list[dict]:
    return load_json(config.history_path(), {}).get(watch_id, [])


def signal(watch_id: str, current: float | None, *, lookback: int = 30) -> dict:
    """Where does `current` sit vs the recent median? Returns {} if too little data."""
    pts = [p["price"] for p in series(watch_id)[-lookback:] if p.get("price") is not None]
    if current is None or len(pts) < 3:
        return {}
    med = median(pts)
    pct = round((current - med) / med * 100, 1) if med else 0.0
    if pct <= -10:
        verdict = "good_deal"
    elif pct >= 10:
        verdict = "high"
    else:
        verdict = "typical"
    return {
        "current": current,
        "median": round(med, 2),
        "low": min(pts),
        "high": max(pts),
        "vs_median_pct": pct,
        "verdict": verdict,
        "samples": len(pts),
    }
