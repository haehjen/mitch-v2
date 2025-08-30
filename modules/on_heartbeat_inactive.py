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

def get_last_input_time():
    if not os.path.exists(LAST_INPUT_PATH):
        return None
    try:
        with open(LAST_INPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return datetime.fromisoformat(data.get("timestamp"))
    except Exception as e:
        logger.warning(f"[on_heartbeat_inactive] Failed to read last input time: {e}")
        return None

def update_last_input_time():
    try:
        with open(LAST_INPUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.utcnow().isoformat()}, f)
    except Exception as e:
        logger.warning(f"[on_heartbeat_inactive] Failed to update last input time: {e}")

def on_heartbeat(system_state):
    now = datetime.utcnow()
    last_input_time = get_last_input_time()

    if last_input_time is None:
        logger.info("[on_heartbeat_inactive] No previous input recorded. Skipping trigger.")
        return

    if now - last_input_time >= INACTIVITY_THRESHOLD:
        logger.info("[on_heartbeat_inactive] Inactivity threshold reached. Triggering echo prompt.")
        event_bus.emit("EMIT_ECHO_PROMPT", {"source": "on_heartbeat_inactive"})
    else:
        logger.debug("[on_heartbeat_inactive] User recently active. No prompt sent.")

def on_input_received(data):
    logger.debug("[on_heartbeat_inactive] Input received — resetting timer.")
    update_last_input_time()

def start_module(event_bus):
    event_bus.subscribe("ECHO_HEARTBEAT", on_heartbeat)
    event_bus.subscribe("EMIT_INPUT_RECEIVED", on_input_received)
    logger.info("[on_heartbeat_inactive] Module loaded and listening for inactivity.")
