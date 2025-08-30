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
ENABLE_INNERMONO_LOG = os.getenv("MITCH_INNERMONO_LOG", "true").lower() == "true"
DEFAULT_PREVIEW_LEN = int(os.getenv("MITCH_EVENT_PREVIEW_LEN", "100"))
INNERMONO_PATH = os.path.join(MITCH_ROOT, "logs", "innermono.log") if ENABLE_INNERMONO_LOG else None

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

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls.__new__(cls)
                cls._instance.__init__()
            return cls._instance

    def set_preview_len(self, n: int):
        try:
            n = int(n)
            self._preview_len = max(0, n)
        except Exception:
            pass

    def mute_console(self, event_type: str):
        self._muted_console.add(event_type)

    def unmute_console(self, event_type: str):
        self._muted_console.discard(event_type)

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

    def emit(self, event_type, data=None):
        ts = datetime.utcnow().isoformat()
        emitter = self._infer_emitter_module()
        if emitter:
            self.registry["emits"][event_type].add(emitter)
            EventRegistry.get_instance().record_emit(event_type, emitter)

        preview = self._summarize(event_type, data, self._preview_len)

        if DEBUG and event_type not in self._muted_console:
            print(f"[{ts}] [EventBus] EMIT: {event_type} -> {preview}")

        # Centralized file logging is handled by core.peterjones.
        # Avoid writing directly to innermono.log here to prevent duplication/noise.

        for callback in list(self.listeners.get(event_type, [])):
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error handling '{event_type}': {e}")

        for callback in list(self.listeners.get("*", [])):
            try:
                callback(event_type, data)
            except Exception as e:
                print(f"[EventBus] Error handling '*' for event '{event_type}': {e}")

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
        try:
            if event_type == "EMIT_PUBLISH_DIGEST" and isinstance(data, dict):
                k = len(data.get("knowledge", []) or [])
                m = len(data.get("memory", []) or [])
                i = len(data.get("innermono", []) or [])
                t = data.get("timestamp", "?")
                keys = list(data.keys())
                return f"{t} | keys={keys} | k={k} m={m} i={i}"

            if data is None:
                return "None"

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

            if isinstance(data, (list, tuple)):
                first = type(data[0]).__name__ if data else "empty"
                return f"list(len={len(data)}, first={first})"

            s = str(data)
            return s[:limit] if limit else s
        except Exception:
            try:
                s = str(data)
                return s[:limit] if limit else s
            except Exception:
                return "(unprintable)"

    def get_registry(self):
        return self.registry

    def get_registered_handlers(self):
        return dict(self.listeners)

# === Singleton instance ===
event_bus = EventBus.get_instance()

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

_env_mute = os.getenv("MITCH_MUTE", "")
if _env_mute:
    for _evt in [x.strip() for x in _env_mute.split(",") if x.strip()]:
        event_bus.mute_console(_evt)
