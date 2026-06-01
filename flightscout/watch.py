"""Watch engine: availability + price alerts with reliable, fire-once delivery.

Watch definitions live in watches.json; per-host runtime state in state.json. The
reliability model:
  * a watch fires ONCE, then stops being probed;
  * detection is latched in state separately from notification, so a transient
    error or notifier outage on the firing day cannot lose the alert (it retries
    until delivery succeeds);
  * N consecutive errored checks send a "watch may be broken" dead-man's-switch
    alert;
  * state writes are atomic and reads tolerate corruption.
"""
from __future__ import annotations

import html
from datetime import date, datetime

from . import config, history
from .search import book_url, search
from .state import load_json, save_json

ERROR_ALERT_THRESHOLD = 3


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- CRUD
def load_watches() -> list[dict]:
    return load_json(config.watches_path(), [])


def save_watches(w: list[dict]) -> None:
    save_json(config.watches_path(), w)


def load_state() -> dict:
    return load_json(config.state_path(), {})


def save_state(s: dict) -> None:
    save_json(config.state_path(), s)


def add_watch(wtype: str, origin: str, dest: str, date_: str, *, cabin: str = "ECONOMY",
              stops: str = "ANY", threshold: float | None = None, label: str = "",
              watch_id: str | None = None) -> dict:
    if wtype not in ("availability", "price"):
        raise ValueError("type must be 'availability' or 'price'")
    if wtype == "price" and threshold is None:
        raise ValueError("price watch requires a --threshold")
    watches = load_watches()
    wid = watch_id or f"{origin}-{dest}-{date_}-{cabin}-{wtype}".lower()
    if any(w["id"] == wid for w in watches):
        raise ValueError(f"watch {wid} already exists")
    w = {
        "id": wid, "type": wtype, "origin": origin, "dest": dest, "date": date_,
        "cabin": cabin, "stops": stops, "label": label, "threshold": threshold,
        "active": True, "created": date.today().isoformat(),
    }
    watches.append(w)
    save_watches(watches)
    return w


def list_watches() -> list[dict]:
    return load_watches()


def remove_watch(wid: str) -> bool:
    watches = load_watches()
    new = [w for w in watches if w["id"] != wid]
    if len(new) == len(watches):
        return False
    save_watches(new)
    state = load_state()
    state.pop(wid, None)
    save_state(state)
    return True


# ---------------------------------------------------------------- evaluation
def evaluate(w: dict) -> tuple[bool, dict]:
    """(fired, info). info carries 'error' on a query failure."""
    try:
        res = search(w["origin"], w["dest"], w["date"], cabin=w.get("cabin"),
                     stops=w.get("stops"), limit=1)
    except Exception as e:  # noqa: BLE001
        return False, {"error": str(e)}
    best = res.best
    info = {"count": res.count, "cheapest": best.to_dict() if best else None}
    if w["type"] == "availability":
        return res.count > 0, info
    price = best.price if best else None
    fired = price is not None and w.get("threshold") is not None and price <= w["threshold"]
    info["threshold"] = w.get("threshold")
    return fired, info


def _fire_message(w: dict, info: dict) -> tuple[str, str, str]:
    c = info.get("cheapest") or {}
    url = book_url(w["origin"], w["dest"], w["date"])
    if w["type"] == "availability":
        subject = f"✈ Bookable now: {w['origin']}→{w['dest']} {w['date']}"
        lead = f"{w['origin']}→{w['dest']} on {w['date']} just opened for booking."
    else:
        subject = f"✈ Fare drop: {w['origin']}→{w['dest']} {w['date']} at {c.get('price')} {c.get('currency','USD')}"
        lead = f"{w['origin']}→{w['dest']} on {w['date']} dropped to {c.get('price')} (≤ {w.get('threshold')})."
    text_lines = [lead]
    html_parts = [f"<p>{html.escape(lead)}</p>"]
    if c:
        air = ", ".join(c.get("airlines") or [])
        via = ", ".join(c.get("via") or [])
        detail = (f"{c.get('price')} {c.get('currency','USD')} · {c.get('stops')} stop(s) · "
                  f"{c.get('duration')} · {air}{' via ' + via if via else ''}")
        text_lines.append(detail)
        text_lines.append(f"Depart {c.get('depart')} → arrive {c.get('arrive')}")
        html_parts.append(f"<p><b>Cheapest:</b> {html.escape(detail)}<br>"
                          f"Depart {html.escape(str(c.get('depart')))} → arrive {html.escape(str(c.get('arrive')))}</p>")
    sig = info.get("signal")
    if sig:
        s = f"vs 30-day median {sig['median']} {c.get('currency','USD')}: {sig['vs_median_pct']}% ({sig['verdict']})"
        text_lines.append(s)
        html_parts.append(f"<p style='color:#555'>{html.escape(s)}</p>")
    text_lines.append(url)
    html_parts.append(f'<p><a href="{html.escape(url)}">Open in Google Flights →</a></p>')
    if w.get("label"):
        html_parts.append(f"<p style='color:#888'>{html.escape(w['label'])}</p>")
    return subject, "".join(html_parts), "\n".join(text_lines)


def _error_message(w: dict, st: dict) -> tuple[str, str, str]:
    subject = f"⚠ Watch may be broken: {w['origin']}→{w['dest']} {w['date']}"
    body = (f"Watch {w['id']} has errored {st.get('error_streak')} checks in a row.\n"
            f"Last error: {st.get('last_error')}\nIt keeps retrying; check flightscout if this persists.")
    html_body = (f"<p>Watch <b>{html.escape(w['id'])}</b> has errored "
                 f"{st.get('error_streak')} checks in a row.</p>"
                 f"<p>Last error: {html.escape(str(st.get('last_error')))}</p>")
    return subject, html_body, body


def check_watches(notifiers=None, *, notify: bool = False, record_history: bool = True,
                  persist: bool = True) -> dict:
    """Evaluate every active watch. Sends via `notifiers` when `notify` is True.

    With no notifiers configured, `--notify` falls back to the console notifier so an
    alert is never silently delivered to nobody. `persist=False` evaluates without
    writing state/history (used by the read-only MCP tool). Safe to run from cron.
    """
    from .notifiers import send_all

    notifiers = notifiers or []
    if notify and not notifiers:  # never "deliver" an alert to an empty list
        from .notifiers.console import ConsoleNotifier
        notifiers = [ConsoleNotifier()]
    watches = load_watches()
    state = load_state()
    fired_now: list[str] = []
    report: list[dict] = []
    live = set()

    for w in watches:
        wid = w["id"]
        live.add(wid)
        if not w.get("active", True):
            continue
        st = state.get(wid, {})

        if st.get("notified"):
            report.append({"id": wid, "status": "done", "notified_at": st.get("notified_at")})
            state[wid] = st
            continue

        fired, info = evaluate(w)
        row = {"id": wid, "fired": fired, **{k: v for k, v in info.items() if k != "cheapest"}}

        if "error" in info:
            st["error_streak"] = st.get("error_streak", 0) + 1
            st["last_error"] = info["error"]
            if st["error_streak"] >= ERROR_ALERT_THRESHOLD and not st.get("error_alerted") and notify:
                try:
                    send_all(notifiers, *_error_message(w, st))
                    st["error_alerted"] = True
                    row["error_escalated"] = True
                except Exception as e:  # noqa: BLE001
                    row["escalation_error"] = str(e)
        else:
            st["error_streak"] = 0
            st.pop("error_alerted", None)
            st["last_count"] = info.get("count")
            price = (info.get("cheapest") or {}).get("price")
            if record_history:
                history.record(wid, price)
                sig = history.signal(wid, price)
                if sig:
                    info["signal"] = sig
                    row["signal"] = sig["verdict"]
            if fired and not st.get("fire_detected_at"):
                st["fire_detected_at"] = _now()
                st["fire_info"] = info

        if st.get("fire_detected_at") and not st.get("notified"):
            fired_now.append(wid)
            if notify:
                try:
                    results = send_all(notifiers, *_fire_message(w, st.get("fire_info") or info))
                    delivered = [k for k, v in results.items() if v is True]
                    if delivered:  # only latch as notified once it actually reached someone
                        st["notified"] = True
                        st["notified_at"] = _now()
                        row["delivered"] = delivered
                    else:
                        row["notify_error"] = "no notifier delivered"
                except Exception as e:  # noqa: BLE001
                    row["notify_error"] = str(e)

        st["last_check"] = date.today().isoformat()
        state[wid] = st
        report.append(row)

    state = {k: v for k, v in state.items() if k in live}
    if persist:
        save_state(state)
    return {"checked": len(report), "fired": fired_now, "results": report}
