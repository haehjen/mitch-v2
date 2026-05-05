import json
import os
from typing import Any

from core.config import MITCH_ROOT
from core.event_bus import event_bus
from core.peterjones import get_logger
from modules import automated_flight_tracker

logger = get_logger("flight_tracker")

_started = False
_subscribed = False
_OUT_PATH = os.path.join(MITCH_ROOT, "modules", "visual", "static", "flight_contacts.json")


def _load_contacts() -> dict[str, Any]:
    try:
        with open(_OUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _on_flight_query(data: dict[str, Any]) -> None:
    if isinstance(data, str):
        text = data
    elif isinstance(data, dict):
        text = data.get("text", "")
    else:
        text = ""
    if not isinstance(text, str):
        return
    text_l = text.lower()

    # Backward-compatible trigger phrases for manual flight status requests.
    if not any(k in text_l for k in ("flight", "flights", "aircraft", "planes")):
        return

    payload = _load_contacts()
    uk = payload.get("uk") or []
    ne = payload.get("ne") or []

    msg = f"Flight tracker online. UK contacts: {len(uk)}. North East contacts: {len(ne)}."
    event_bus.emit("EMIT_SPEAK", {"text": msg, "source": "status"})


def start_module(_event_bus):
    global _started, _subscribed
    if _started:
        return
    _started = True

    # Ensure the active polling implementation is running.
    automated_flight_tracker.start_module(event_bus)

    if not _subscribed:
        event_bus.subscribe("EMIT_INPUT_RECEIVED", _on_flight_query)
        _subscribed = True

    logger.info("FlightTracker compatibility module started (delegating to automated_flight_tracker).")
