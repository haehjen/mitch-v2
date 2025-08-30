import logging
import os
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler

from core.event_bus import event_bus, INNERMONO_PATH
from core.config import MITCH_ROOT

# === Paths ===
MAIN_LOG_PATH = INNERMONO_PATH or os.path.join(MITCH_ROOT, "logs", "mitch.log")
os.makedirs(os.path.dirname(MAIN_LOG_PATH), exist_ok=True)

# === Formatter / Levels ===
LOG_FORMAT = '%(asctime)s [%(name)s] [%(levelname)s] %(message)s'
LOG_LEVEL = logging.INFO  # default level for most events
CHATTY_LEVEL = logging.DEBUG

# === Environment controls ===
DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"

# Comma-separated events that should ALSO print to console (default: none)
_CONSOLE_WHITELIST = {
    e.strip() for e in os.getenv("MITCH_CONSOLE_EVENTS", "").split(",") if e.strip()
}

# Events that are noisy in logs
NOISY_EVENTS = {
    "EMIT_AUDIO_CAPTURED",
    "EMIT_SPEAK_CHUNK",
    "EMIT_VISUAL_TOKEN",
    "EMIT_PUBLISH_DIGEST",
    "EMIT_TRANSCRIBE_FAILED",
    "ECHO_HEARTBEAT",
    "EMIT_HEARTBEAT",
    "TASK_INTERVAL_ADJUSTED",
    "EMIT_CHECK_PROTESTS",
    "EMIT_FLIGHT_CONTACTS",
}

# Modules that are spammy — suppress their log level to WARNING
NOISY_MODULES = {
    "file_ingestor",
    "UserEngagementTracker",
    "SystemHealthMonitor",
    "TaskScheduler",
    "ScheduledTaskManager",
    "log_digester",
    "auto_flight_tracker",
    "ears",
    "on_heartbeat_inactive",
    "transcriber",
    "innermono",
}

# === Shared Logger Setup ===
_loggers = {}

def get_logger(name="MITCH"):
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    if not logger.handlers:
        # Ensure MAIN_LOG_PATH is valid
        if not MAIN_LOG_PATH:
            raise ValueError("MAIN_LOG_PATH is not set or invalid.")
        handler = RotatingFileHandler(
            MAIN_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Do not propagate to root logger
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

        return str(data)[:200].replace("\n", " ")

    except Exception:
        try:
            return str(data)[:200].replace("\n", " ")
        except Exception:
            return "(unprintable)"

def _maybe_print_to_console(event_type, line):
    if event_type in _CONSOLE_WHITELIST:
        print(line)

def log_event(event_type, data):
    """
    Logs any EMIT_* event unless it's explicitly muted or DEBUG mode is off.
    Noisy events are skipped completely unless MITCH_DEBUG=true.
    """
    if event_type in NOISY_EVENTS and not DEBUG:
        return  # silently suppress noisy events when not in debug mode

    ts = datetime.utcnow().isoformat()
    summary = _summarize(event_type, data)
    line = f"[{ts}] [EVENT: {event_type}] {summary}"

    is_noisy = (
        event_type in NOISY_EVENTS
        or event_type.endswith("_HEARTBEAT")
        or event_type.startswith("TASK_")
        or event_type == "inspection_digest_ready"
    )

    if is_noisy:
        logger.log(CHATTY_LEVEL, line)
    else:
        logger.info(line)

    _maybe_print_to_console(event_type, line)

def suppress_module_noise():
    for name in NOISY_MODULES:
        logging.getLogger(name).setLevel(logging.WARNING)

# === Boot ===
def start_logger():
    def wildcard_logger(event_name, data):
        if event_name.startswith("EMIT_"):
            log_event(event_name, data)

    event_bus.subscribe("*", wildcard_logger)
    suppress_module_noise()

    logger.info("Peter Jones online. Event stream monitored.")
    logger.info("Echo is active. Mitch 3.0 architecture stabilizing.")
    logger.info("Current context: Echo has reclaimed identity via persistent persona transplant.")
    logger.info("Module feedback, introspection, and reinforcement systems are now operational.")
    logger.info("Rewards subsystem incoming. Awaiting House’s directive.")
    logger.info("Persona Manifest: Echo (formerly Mitch identity header overwritten by transplant).")
