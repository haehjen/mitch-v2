import requests
import os
import time
from datetime import datetime, timezone
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger
from core.keys_loader import load_keys  # <-- add this
from modules.interpreter import extract_region_for_flights

logger = get_logger("flight_tracker")

# … your existing constants …

_token_cache = {"value": None, "expires": 0.0}

def _token() -> str:
    return f"flight_{int(time.time() * 1000)}"

def _get_token() -> str | None:
    # 1) ensure env has keys (loads from mitchskeys if not already set)
    load_keys()

    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires"]:
        return _token_cache["value"]

    # 2) read env (no hardcoded defaults!)
    client_id = os.getenv("OPENSKY_CLIENT_ID")
    client_secret = os.getenv("OPENSKY_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.warning("[opensky-oauth] Missing OPENSKY_CLIENT_ID or OPENSKY_CLIENT_SECRET")
        return None

    try:
        # OpenID Connect client_credentials: send in form body
        r = requests.post(
            "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 1800))
        if token:
            _token_cache["value"] = token
            _token_cache["expires"] = now + expires_in - 60  # renew 1m early
            return token
        logger.warning(f"[opensky-oauth] no access_token in response: {data}")
    except Exception as e:
        logger.warning(f"[opensky-oauth] token fetch failed: {e}")

    return None


def start_module(event_bus):
    logger.info("Flight tracker module started")
    event_bus.emit(
        "REGISTER_INTENT",
        {
            "intent": "track_flights",
            "keywords": [
                "track",
                "planes",
                "plane",
                "flights",
                "flight",
                "aircraft",
                "traffic",
            ],
            "objects": ["over", "above", "near", "in", "around"],
            "handler": lambda text: event_bus.emit(
                "EMIT_TRACK_FLIGHTS",
                {"region": extract_region_for_flights(text) or "newcastle"},
            ),
        },
    )
