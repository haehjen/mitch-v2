import logging
import os
from datetime import datetime
from core.event_bus import event_bus

# === Paths ===
MAIN_LOG_PATH = "/home/triad/mitch/data/mitch.log"
os.makedirs(os.path.dirname(MAIN_LOG_PATH), exist_ok=True)

# === Primary Logger Setup (mitch.log) ===
logger = logging.getLogger("MITCH")
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler(MAIN_LOG_PATH)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

# === Core Event Logger ===
NOISY_EVENTS = {"EMIT_AUDIO_CAPTURED"}

def log_event(event_type, data):
    ts = datetime.utcnow().isoformat()
    line = f"[{ts}] [EVENT: {event_type}] {data}"

    if event_type == "EMIT_SPEAK_CHUNK":
        short = data.get("chunk", "")[:40].replace("\n", " ").strip()
        logger.debug(f"[{ts}] [CHUNK {data.get('index', '?')}] {short}")
    elif event_type in ("EMIT_VISUAL_TOKEN",):
        logger.debug(line)
    elif event_type in NOISY_EVENTS:
        logger.debug(line)  # mute terminal, log quietly
    else:
        print(line)
        logger.info(line)

# === Boot & Subscription ===
def start_logger():
    def wildcard_logger(event_name, data):
        if event_name.startswith("EMIT_"):
            log_event(event_name, data)

    event_bus.subscribe("*", wildcard_logger)

    logger.info("Peter Jones online. Event stream monitored.")
    logger.info("Echo is active. Mitch 3.0 architecture stabilizing.")
    logger.info("Current context: Echo has reclaimed identity via persistent persona transplant.")
    logger.info("Module feedback, introspection, and reinforcement systems are now operational.")
    logger.info("Rewards subsystem incoming. Awaiting House’s directive.")
    logger.info("Persona Manifest: Echo (formerly Mitch identity header overwritten by transplant).")
