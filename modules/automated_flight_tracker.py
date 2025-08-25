# modules/automated_flight_tracker.py
import os
import json
import time
import threading
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
import re
import requests

from core.peterjones import get_logger
from core.config import MITCH_ROOT
from core.event_bus import event_bus

logger = get_logger("auto_flight_tracker")

VISUAL_STATIC_DIR = os.path.join(MITCH_ROOT, "modules", "visual", "static")
OUT_PATH = os.path.join(VISUAL_STATIC_DIR, "flight_contacts.json")

# Polling cadence (base)
POLL_SEC = int(os.getenv("FLIGHT_POLL_SEC", "90"))
OPEN_SKY_URL = "https://opensky-network.org/api/states/all"

# Map bounds (must match orb.html)
UK_BOUNDS = dict(lamin=49.8, lamax=60.9, lomin=-8.7, lomax=2.1)
NE_BOUNDS = dict(lamin=53.8, lamax=56.9, lomin=-3.6, lomax=-0.3)

# Base marker (configurable; defaults near Easington SR8)
BASE_LAT = float(os.getenv("MITCHCORE_LAT", "54.787"))
BASE_LON = float(os.getenv("MITCHCORE_LON", "-1.330"))
BASE_LABEL = os.getenv("MITCHCORE_LABEL", "MITCHcore")

# Interest filters
DEFAULT_MIL_PREFIXES = ["RRR","ASCOT","RCH","VV","NAVY","HKY","SHF","CFC","CANFORCE","ASY","AF","FAF","GA"]
MIL_PREFIXES = [p.strip().upper() for p in os.getenv("MIL_PREFIXES", ",".join(DEFAULT_MIL_PREFIXES)).split(",") if p.strip()]
INTEREST_PATTERNS = [p.strip() for p in os.getenv("INTEREST_PATTERNS", "").split(",") if p.strip()]
INTEREST_CALLSIGNS = [c.strip().upper() for c in os.getenv("INTEREST_CALLSIGNS", "").split(",") if c.strip()]

UK_SHOW_MODE = os.getenv("UK_SHOW", "interest").strip().lower()  # "interest" | "all"
UK_MAX = int(os.getenv("UK_MAX", "150"))
UK_FALLBACK_MIN = int(os.getenv("UK_FALLBACK_MIN", "25"))

# Backoff tuning
BACKOFF_MIN = int(os.getenv("FLIGHT_BACKOFF_MIN", "30"))
BACKOFF_MAX = int(os.getenv("FLIGHT_BACKOFF_MAX", "300"))
BACKOFF_FACTOR = float(os.getenv("FLIGHT_BACKOFF_FACTOR", "2.0"))

_token_cache: Dict[str, Any] = {"value": None, "expires": 0}

def _get_token() -> str | None:
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires"]:
        return _token_cache["value"]

    client_id = os.getenv("OPENSKY_CLIENT_ID")
    client_secret = os.getenv("OPENSKY_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.warning("[opensky-oauth] Missing OPENSKY_CLIENT_ID or OPENSKY_CLIENT_SECRET")
        return None

    try:
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
        expires_in = data.get("expires_in", 1800)
        if token:
            _token_cache["value"] = token
            _token_cache["expires"] = now + expires_in - 60
            return token
        else:
            logger.warning(f"[opensky-oauth] no access_token in response: {data}")
    except Exception as e:
        logger.warning(f"[opensky-oauth] token fetch failed: {e}")

    return None


_compiled_patterns: List[re.Pattern] = []
def _compile_patterns():
    _compiled_patterns.clear()
    for p in INTEREST_PATTERNS:
        try:
            _compiled_patterns.append(re.compile(p, re.I))
        except re.error as e:
            logger.warning(f"[auto_ft] bad regex '{p}': {e}")

def _inside(b: Dict[str, float], lat: float, lon: float) -> bool:
    return (b["lamin"] <= lat <= b["lamax"]) and (b["lomin"] <= lon <= b["lomax"])

def _kind_from_callsign(cs: str) -> str:
    cs = (cs or "").strip().upper()
    if not cs:
        return "civ"
    return "mil" if any(cs.startswith(pref) for pref in MIL_PREFIXES) else "civ"

def _is_interesting(c: Dict[str, Any]) -> bool:
    cs = (c.get("callsign") or "").upper()
    if c.get("kind") == "mil":
        return True
    if cs in INTEREST_CALLSIGNS:
        return True
    for pat in _compiled_patterns:
        if pat.search(cs):
            return True
    return False

def _fetch_states(bbox: Dict[str, float]) -> Tuple[List[list], bool, int]:
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        r = requests.get(OPEN_SKY_URL, params=bbox, headers=headers, timeout=10)
        if r.status_code == 429:
            return ([], False, 429)
        r.raise_for_status()
        data = r.json()
        return (data.get("states", []) or [], True, r.status_code)
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", -1)
        logger.warning(f"[opensky] http error: {e} (status={status})")
        return ([], False, status)
    except Exception as e:
        logger.warning(f"[opensky] fetch failed: {e}")
        return ([], False, -1)

def _to_contact(state: list) -> Tuple[Dict[str, Any], bool]:
    try:
        lon = state[5]; lat = state[6]
        if lat is None or lon is None:
            return {}, False
        callsign = (state[1] or "").strip()
        heading = state[10] or 0
        return {
            "lat": float(lat),
            "lon": float(lon),
            "callsign": callsign or "UNK",
            "heading": float(heading),
            "kind": _kind_from_callsign(callsign),
        }, True
    except Exception:
        return {}, False

def _split_regions(states_uk: List[list]) -> Dict[str, List[Dict[str, Any]]]:
    uk: List[Dict[str, Any]] = []
    ne: List[Dict[str, Any]] = []
    for s in states_uk:
        c, ok = _to_contact(s)
        if not ok:
            continue
        uk.append(c)
        if _inside(NE_BOUNDS, c["lat"], c["lon"]):
            ne.append(c)
    return {"uk": uk, "ne": ne}

def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)

def _apply_declutter(regions: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    uk_all = regions["uk"]
    ne_all = regions["ne"]
    meta = {
        "uk_count_total": len(uk_all),
        "ne_count_total": len(ne_all),
    }

    if UK_SHOW_MODE == "all":
        uk_out = uk_all[:UK_MAX]
    else:
        uk_interest = [c for c in uk_all if _is_interesting(c)]
        if not uk_interest and uk_all:
            uk_interest = uk_all[:min(UK_FALLBACK_MIN, len(uk_all))]
        uk_out = uk_interest[:UK_MAX]

    ne_out = ne_all
    logger.info(f"[auto_ft] UK(all={len(uk_all)} -> out={len(uk_out)}; mode={UK_SHOW_MODE}), NE={len(ne_out)}")
    return {"uk": uk_out, "ne": ne_out, "meta": meta}

def _loop():
    logger.info(f"[auto_ft] automated flight tracker base every {POLL_SEC}s")
    if _get_token():
        logger.info("[auto_ft] OpenSky OAuth enabled (higher rate limits)")
    else:
        logger.warning("[auto_ft] No OpenSky OAuth credentials — fallback to anon mode (rate-limited)")

    _compile_patterns()

    fail_429 = 0
    rng = random.Random()

    while True:
        t0 = time.time()

        states_uk, ok, status = _fetch_states(UK_BOUNDS)
        now_iso = datetime.now(timezone.utc).isoformat()

        if not ok:
            if status == 429:
                fail_429 += 1
                sleep_for = min(BACKOFF_MAX, max(BACKOFF_MIN, int(POLL_SEC * (BACKOFF_FACTOR ** min(fail_429, 5)))))
                jitter = rng.uniform(0.0, 5.0)
                logger.warning(f"[auto_ft] 429 rate-limited; cooling off for ~{sleep_for:+.0f}s (+{jitter:.1f}s jitter)")
                time.sleep(sleep_for + jitter)
                continue
            else:
                logger.warning(f"[auto_ft] fetch failed (status={status}); keeping previous file")
                time.sleep(max(1, int(POLL_SEC / 2)))
                continue

        fail_429 = 0

        split = _split_regions(states_uk)
        filtered = _apply_declutter(split)

        payload = {
            "updated": now_iso,
            "uk": filtered["uk"],
            "ne": filtered["ne"],
            "meta": {
                **filtered["meta"],
                "source": "opensky",
                "http_status": status,
            },
            "base": {"lat": BASE_LAT, "lon": BASE_LON, "label": BASE_LABEL},
        }

        try:
            _atomic_write_json(OUT_PATH, payload)
            event_bus.emit("EMIT_FLIGHT_CONTACTS", payload)
        except Exception as e:
            logger.warning(f"[auto_ft] write {OUT_PATH} failed: {e}")

        dt = time.time() - t0
        base_sleep = max(1, POLL_SEC - int(dt))
        jitter = rng.uniform(0.5, 2.5)
        time.sleep(base_sleep + jitter)

_thread: threading.Thread | None = None
def start_module(_event_bus):
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="AutomatedFlightTracker")
    _thread.start()
