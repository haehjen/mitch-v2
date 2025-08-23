# core/event_bus.py
from collections import defaultdict
from threading import Lock
from datetime import datetime
import inspect
import os
import json
import requests
from core.config import MITCH_ROOT
from core.event_registry import EventRegistry

# --- Configuration ---
DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"
DEFAULT_PREVIEW_LEN = int(os.getenv("MITCH_EVENT_PREVIEW_LEN", "100"))
INNERMONO_PATH = os.path.join(MITCH_ROOT, "logs", "innermono.log")

# Events that are noisy in console; muted from stdout (still logged to file)
DEFAULT_MUTED_CONSOLE_EVENTS = {
    "EMIT_PUBLISH_DIGEST",
}

class EventBus:
    _instance = None
    _lock = Lock()

    def __init__(self):
        if not hasattr(self, "listeners"):
            self.listeners = defaultdict(list)
            self.registry = {
                "subscriptions": defaultdict(set),  # event_type -> set(modules)
                "emits": defaultdict(set),         # event_type -> set(modules)
            }
            self._preview_len = DEFAULT_PREVIEW_LEN
            self._muted_console = set(DEFAULT_MUTED_CONSOLE_EVENTS)

    # ---------- Singleton ----------
    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls.__new__(cls)
                cls._instance.__init__()  # manual init on singleton
            return cls._instance

    # ---------- Controls ----------
    def set_preview_len(self, n: int):
        """Set max characters for console/file preview (non-negative)."""
        try:
            n = int(n)
            self._preview_len = max(0, n)
        except Exception:
            pass

    def mute_console(self, event_type: str):
        """Mute console prints for this event (still writes to innermono and calls listeners)."""
        self._muted_console.add(event_type)

    def unmute_console(self, event_type: str):
        """Unmute console prints for this event."""
        self._muted_console.discard(event_type)

    # ---------- Subscription API ----------
    def subscribe(self, event_type, callback):
        callback_id = f"{callback.__module__}.{callback.__name__}"
        if callback not in self.listeners[event_type]:
            self.listeners[event_type].append(callback)
            self.registry["subscriptions"][event_type].add(callback.__module__)
            EventRegistry.get_instance().record_subscribe(event_type, callback.__module__)
            if DEBUG:
                print(f"[EventBus] Subscribed to {event_type}: {callback_id}")
        else:
            if DEBUG:
                print(f"[EventBus] SKIPPED duplicate subscribe: {event_type} -> {callback_id}")

    def unsubscribe(self, event_type, callback):
        if callback in self.listeners[event_type]:
            self.listeners[event_type].remove(callback)
            if DEBUG:
                print(f"[EventBus] Unsubscribed from {event_type}: {callback.__module__}.{callback.__name__}")

    # ---------- Emit ----------
    def emit(self, event_type, data=None):
        ts = datetime.utcnow().isoformat()
        emitter = self._infer_emitter_module()
        if emitter:
            self.registry["emits"][event_type].add(emitter)
            EventRegistry.get_instance().record_emit(event_type, emitter)

        # Build compact preview (digest etc. summarized)
        preview = self._summarize(event_type, data, self._preview_len)

        # Console trace (respect mute list)
        if DEBUG and event_type not in self._muted_console:
            print(f"[{ts}] [EventBus] EMIT: {event_type} -> {preview}")

        # innermono log: always write compact preview (never full blobs)
        try:
            os.makedirs(os.path.dirname(INNERMONO_PATH), exist_ok=True)
            with open(INNERMONO_PATH, "a", encoding="utf-8") as f:
                f.write(f"{ts} [{event_type}] {preview}\n")
        except Exception as e:
            if DEBUG:
                print(f"[EventBus] Failed to write to innermono.log: {e}")

        # Notify specific listeners
        for callback in list(self.listeners.get(event_type, [])):
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error handling '{event_type}': {e}")

        # Notify wildcard listeners
        for callback in list(self.listeners.get("*", [])):
            try:
                callback(event_type, data)
            except Exception as e:
                print(f"[EventBus] Error handling '*' for event '{event_type}': {e}")

    # ---------- Helpers ----------
    def _infer_emitter_module(self):
        try:
            frame = inspect.currentframe()
            while frame:
                mod = inspect.getmodule(frame)
                if mod and mod.__name__ != __name__ and not mod.__name__.startswith("threading"):
                    return mod.__name__
                frame = frame.f_back
        except Exception:
            pass
        return "unknown"

    def _summarize(self, event_type: str, data, limit: int) -> str:
        """Return a small, safe preview string for console/file logs."""
        try:
            if event_type == "EMIT_PUBLISH_DIGEST" and isinstance(data, dict):
                k = len(data.get("knowledge", []) or [])
                m = len(data.get("memory", []) or [])
                i = len(data.get("innermono", []) or [])
                t = data.get("timestamp", "?")
                keys = list(data.keys())
                return f"{t} | keys={keys} | k={k} m={m} i={i}"

            # Generic summarization
            if data is None:
                return "None"

            # Dict: show keys and some scalar previews
            if isinstance(data, dict):
                parts = []
                for k, v in data.items():
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        parts.append(f"{k}={str(v)[:limit]}")
                    elif isinstance(v, list):
                        parts.append(f"{k}[{len(v)}]")
                    elif isinstance(v, dict):
                        parts.append(f"{k}{{{len(v)}}}")
                    else:
                        parts.append(f"{k}<{type(v).__name__}>")
                s = ", ".join(parts)
                return s[:limit] if limit else s

            # List/tuple: just show length and first item type
            if isinstance(data, (list, tuple)):
                first = type(data[0]).__name__ if data else "empty"
                return f"list(len={len(data)}, first={first})"

            # Fallback to string truncation
            s = str(data)
            return s[:limit] if limit else s
        except Exception:
            # Never let preview generation crash emit()
            try:
                s = str(data)
                return s[:limit] if limit else s
            except Exception:
                return "(unprintable)"

    # ---------- Introspection ----------
    def get_registry(self):
        return self.registry

    def get_registered_handlers(self):
        return dict(self.listeners)

# === Singleton instance ===
event_bus = EventBus.get_instance()

# === Built-in listener for EMIT_SPEAK (unchanged) ===
def _log_emit_speak(data):
    if not data:
        return
    text = data.get("text") if isinstance(data, dict) else None
    if text and (not isinstance(data, dict) or data.get("source") != "status"):
        try:
            requests.post("http://localhost:5000/emit_response", json={"text": text})
        except Exception as e:
            if DEBUG:
                print(f"[EventBus] Failed to forward EMIT_SPEAK to visual log: {e}")

event_bus.subscribe("EMIT_SPEAK", _log_emit_speak)

# --- Optional: allow muting via env list, e.g. MITCH_MUTE="EMIT_PUBLISH_DIGEST,NOISY_EVENT" ---
_env_mute = os.getenv("MITCH_MUTE", "")
if _env_mute:
    for _evt in [x.strip() for x in _env_mute.split(",") if x.strip()]:
        event_bus.mute_console(_evt)
