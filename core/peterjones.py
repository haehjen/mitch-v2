import logging
import os
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler

from core.event_bus import event_bus, INNERMONO_PATH
from core.config import MITCH_ROOT

# === Paths ===
MAIN_LOG_PATH = INNERMONO_PATH
os.makedirs(os.path.dirname(MAIN_LOG_PATH), exist_ok=True)

# === Formatter / Levels ===
LOG_FORMAT = '%(asctime)s [%(name)s] [%(levelname)s] %(message)s'
LOG_LEVEL = logging.INFO  # default level for most events
CHATTY_LEVEL = logging.DEBUG

# === Environment controls ===
# Comma-separated events that should ALSO print to console (default: none)
_CONSOLE_WHITELIST = {
    e.strip() for e in os.getenv("MITCH_CONSOLE_EVENTS", "").split(",") if e.strip()
}
# Noisy events that we always downshift to DEBUG in file logs
NOISY_EVENTS = {
    "EMIT_AUDIO_CAPTURED",
    "EMIT_SPEAK_CHUNK",
    "EMIT_VISUAL_TOKEN",
    "EMIT_PUBLISH_DIGEST",  # <- specifically tame this
}

# === Shared Logger Setup ===
_loggers = {}

def get_logger(name="MITCH"):
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    if not logger.handlers:
        handler = RotatingFileHandler(MAIN_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Do not propagate to root to avoid any accidental console handlers elsewhere
    logger.propagate = False

    _loggers[name] = logger
    return logger

# === Default Core Logger ===
logger = get_logger("MITCH")

def _summarize(event_type, data):
    """
    Produce a compact, single-line summary for logs without dumping huge payloads.
    """
    try:
        if event_type == "EMIT_PUBLISH_DIGEST" and isinstance(data, dict):
            k = len(data.get("knowledge", []) or [])
            m = len(data.get("memory", []) or [])
            i = len(data.get("innermono", []) or [])
            t = data.get("timestamp", "?")
            keys = list(data.keys())
            return f"{t} | keys={keys} | k={k} m={m} i={i}"

        if isinstance(data, dict):
            # Show only scalars and sizes
            parts = []
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    sval = str(v)
                    parts.append(f"{k}={sval[:80].replace(os.linesep, ' ')}")
                elif isinstance(v, list):
                    parts.append(f"{k}[{len(v)}]")
                elif isinstance(v, dict):
                    parts.append(f"{k}{{{len(v)}}}")
                else:
                    parts.append(f"{k}<{type(v).__name__}>")
            return ", ".join(parts)

        if isinstance(data, list):
            return f"list(len={len(data)})"

        if data is None:
            return "None"

        s = str(data)
        return s[:200].replace("\n", " ")
    except Exception:
        try:
            return str(data)[:200].replace("\n", " ")
        except Exception:
            return "(unprintable)"

def _maybe_print_to_console(event_type, line):
    # Only print if explicitly whitelisted
    if event_type in _CONSOLE_WHITELIST:
        print(line)

def log_event(event_type, data):
    ts = datetime.utcnow().isoformat()
    summary = _summarize(event_type, data)
    line = f"[{ts}] [EVENT: {event_type}] {summary}"

    # File logging: downshift super-noisy events to DEBUG
    if event_type in NOISY_EVENTS:
        logger.log(CHATTY_LEVEL, line)
    else:
        logger.info(line)

    # Console printing: ONLY if whitelisted via env
    _maybe_print_to_console(event_type, line)

# === Boot & Subscription ===
def start_logger():
    def wildcard_logger(event_name, data):
        # Only log EMIT_* to avoid internal housekeeping noise
        if event_name.startswith("EMIT_"):
            log_event(event_name, data)

    event_bus.subscribe("*", wildcard_logger)

    # Startup context messages -> file only (no console)
    logger.info("Peter Jones online. Event stream monitored.")
    logger.info("Echo is active. Mitch 3.0 architecture stabilizing.")
    logger.info("Current context: Echo has reclaimed identity via persistent persona transplant.")
    logger.info("Module feedback, introspection, and reinforcement systems are now operational.")
    logger.info("Rewards subsystem incoming. Awaiting House’s directive.")
    logger.info("Persona Manifest: Echo (formerly Mitch identity header overwritten by transplant).")
