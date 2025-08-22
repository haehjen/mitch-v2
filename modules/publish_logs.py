import threading
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from collections import deque

# ---- SINGLETON EVENT BUS ----
from core.event_bus import event_bus as BUS
from core.config import MITCH_ROOT

# ---- CONFIG ----
DIGEST_INTERVAL = 30  # seconds
OUTPUT_PATH     = Path(MITCH_ROOT) / "data/recent_digest.json"
KNOWLEDGE_PATH  = Path(MITCH_ROOT) / "data/knowledge.json"
MEMORY_PATH     = Path(MITCH_ROOT) / "data/memory.jsonl"
INSPECTION_PATH = Path(MITCH_ROOT) / "logs/inspection_digest.json"
INNERMONO_PATH  = Path(MITCH_ROOT) / "logs/innermono.log"
LOG_PATH        = Path(MITCH_ROOT) / "logs/digest_publisher.log"

VERBOSE_CONSOLE = False         # set True if you want console prints
MAX_LOG_BYTES   = 512_000       # 512KB per log file
BACKUP_COUNT    = 3             # keep 3 rotated files
EMIT_MIN_SECS   = 0             # optional: set >0 to rate-limit emits

# ---- MODULE-LEVEL STATE (idempotency) ----
_THREAD  = None
_STARTED = False
_LAST_EMIT_TS = 0.0

# ---- LOGGER SETUP ----
def _setup_logger() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("digest_publisher")
    if logger.handlers:
        return logger  # already configured
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False  # don't bubble to root (avoids console spam)
    return logger

LOGGER = _setup_logger()

# ---- UTILITIES ----
def _tail_lines(path: Path, limit: int):
    """Memory-safe tail: read last N lines as strings (no newlines)."""
    if not path.exists():
        return []
    buf = deque(maxlen=limit)
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                buf.append(line.rstrip("\n"))
    except Exception as e:
        return [f"[Error reading {path.name}: {e}]"]
    return list(buf)

def _read_json(path: Path, default):
    """Read a JSON file defensively; return default on error/non-existence."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception as e:
        # return default if provided, else surface the error
        return default if default is not None else {"error": str(e)}

def _read_jsonl_tail(path: Path, limit: int):
    """Parse last N JSONL records into dicts, falling back to raw line on error."""
    out = []
    for line in _tail_lines(path, limit):
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"raw": line})
    return out

def _safe_emit(payload: dict):
    """Optional rate-limited emit to reduce downstream noise."""
    global _LAST_EMIT_TS
    if EMIT_MIN_SECS > 0:
        now = time.time()
        if now - _LAST_EMIT_TS < EMIT_MIN_SECS:
            return
        _LAST_EMIT_TS = now
    BUS.emit("EMIT_PUBLISH_DIGEST", payload)

# ---- THREAD ----
class DigestPublisherThread(threading.Thread):
    def __init__(self, interval: int = DIGEST_INTERVAL):
        super().__init__(daemon=True, name="DigestPublisher")
        self.interval = interval
        self._stop_event = threading.Event()

    def shutdown(self):
        self._stop_event.set()
        if VERBOSE_CONSOLE:
            print("[DigestPublisher] Shutdown signal received.")
        LOGGER.info("Shutdown signal received.")

    def build_digest(self) -> dict:
        digest = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "knowledge": [],
            "memory": [],
            "inspection": {},
            "innermono": []
        }

        # knowledge.json -> expect list; take last 8 safely
        knowledge = _read_json(KNOWLEDGE_PATH, default=[])
        if isinstance(knowledge, list):
            digest["knowledge"] = knowledge[-8:]
        elif isinstance(knowledge, dict):
            # if stored as dict by mistake, surface a compact preview
            digest["knowledge"] = [{"key": k, "value": v} for k, v in list(knowledge.items())[-8:]]
        else:
            digest["knowledge"] = [f"[Unsupported knowledge type: {type(knowledge).__name__}]"]

        # memory.jsonl -> last 8 JSONL entries (parsed)
        digest["memory"] = _read_jsonl_tail(MEMORY_PATH, limit=8)

        # inspection_digest.json -> JSON object
        inspection = _read_json(INSPECTION_PATH, default={})
        digest["inspection"] = inspection if isinstance(inspection, dict) else {"raw": inspection}

        # innermono.log -> last 15 lines (strings)
        digest["innermono"] = _tail_lines(INNERMONO_PATH, limit=15)

        return digest

    def run(self):
        start_msg = f"[DigestPublisher] Thread started. Interval: {self.interval}s"
        if VERBOSE_CONSOLE:
            print(start_msg)
        LOGGER.info("Thread started. Interval: %ss", self.interval)

        while not self._stop_event.is_set():
            try:
                digest = self.build_digest()

                # write latest digest snapshot
                OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(digest, f, indent=2)

                # emit to bus (rate-limited if configured)
                _safe_emit(digest)

                # log only a compact summary
                LOGGER.info(
                    "Published digest | knowledge:%d memory:%d innermono:%d",
                    len(digest.get("knowledge", [])),
                    len(digest.get("memory", [])),
                    len(digest.get("innermono", [])),
                )
            except Exception as e:
                err_payload = {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}
                try:
                    _safe_emit(err_payload)
                except Exception:
                    pass
                LOGGER.exception("Digest publish failed: %s", e)

            # sleep or exit early on shutdown
            self._stop_event.wait(self.interval)

# ---- PUBLIC API ----
def start_module(_ignored=None):
    """
    Entry point for the Digest Publisher module.
    Always uses the singleton BUS. Idempotent (won't start twice).
    """
    global _THREAD, _STARTED
    if _STARTED and _THREAD and _THREAD.is_alive():
        if VERBOSE_CONSOLE:
            print("[DigestPublisher] Already running; skipping second start.")
        LOGGER.info("Start requested but already running; skipping.")
        return

    _THREAD = DigestPublisherThread(interval=DIGEST_INTERVAL)
    _THREAD.start()
    _STARTED = True

    start_msg = f"[DigestPublisher] Module started and publishing digest every {DIGEST_INTERVAL}s."
    if VERBOSE_CONSOLE:
        print(start_msg)
    LOGGER.info("Module started; interval=%ss", DIGEST_INTERVAL)

def shutdown_module():
    """Optional: call at app shutdown to stop the thread cleanly."""
    global _THREAD, _STARTED
    if _THREAD and _THREAD.is_alive():
        _THREAD.shutdown()
        _THREAD.join(timeout=5)
    _THREAD = None
    _STARTED = False
    LOGGER.info("Module stopped.")
