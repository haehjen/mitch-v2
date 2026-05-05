import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

logger = get_logger("on_heartbeat_inactive")

LAST_INPUT_PATH = os.path.join(MITCH_ROOT, "data", "last_input_seen.json")

# Time to wait after last input before triggering introspection
INACTIVITY_THRESHOLD = timedelta(minutes=25)

def _read_state():
    if not os.path.exists(LAST_INPUT_PATH):
        return {}
    try:
        with open(LAST_INPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"[on_heartbeat_inactive] Failed to read last input state: {e}")
        return {}


def _write_state(state):
    try:
        with open(LAST_INPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning(f"[on_heartbeat_inactive] Failed to persist input state: {e}")


def get_last_input_time():
    data = _read_state()
    value = data.get("timestamp")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception as e:
        logger.warning(f"[on_heartbeat_inactive] Invalid input timestamp format: {e}")
        return None


def get_last_prompt_for_input():
    data = _read_state()
    return str(data.get("last_prompt_for_input_ts", "") or "")


def mark_prompted_for_current_input():
    data = _read_state()
    current_input_ts = str(data.get("timestamp", "") or "")
    if not current_input_ts:
        return
    data["last_prompt_for_input_ts"] = current_input_ts
    _write_state(data)


def update_last_input_time():
    now_ts = datetime.utcnow().isoformat()
    state = _read_state()
    state["timestamp"] = now_ts
    # New input resets inactivity prompt latch for the next quiet period.
    state["last_prompt_for_input_ts"] = ""
    _write_state(state)

def on_heartbeat(system_state):
    now = datetime.utcnow()
    last_input_time = get_last_input_time()

    if last_input_time is None:
        logger.info("[on_heartbeat_inactive] No previous input recorded. Skipping trigger.")
        return

    if now - last_input_time >= INACTIVITY_THRESHOLD:
        state = _read_state()
        current_input_ts = str(state.get("timestamp", "") or "")
        last_prompt_for_input_ts = get_last_prompt_for_input()
        if current_input_ts and current_input_ts == last_prompt_for_input_ts:
            logger.debug("[on_heartbeat_inactive] Inactivity already prompted for current input window.")
            return
        logger.info("[on_heartbeat_inactive] Inactivity threshold reached. Triggering echo prompt.")
        event_bus.emit("EMIT_ECHO_PROMPT", {"source": "on_heartbeat_inactive"})
        mark_prompted_for_current_input()
    else:
        logger.debug("[on_heartbeat_inactive] User recently active. No prompt sent.")

def on_input_received(data):
    logger.debug("[on_heartbeat_inactive] Input received — resetting timer.")
    update_last_input_time()

def start_module(event_bus):
    event_bus.subscribe("ECHO_HEARTBEAT", on_heartbeat)
    event_bus.subscribe("EMIT_INPUT_RECEIVED", on_input_received)
    logger.info("[on_heartbeat_inactive] Module loaded and listening for inactivity.")
