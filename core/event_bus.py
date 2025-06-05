from collections import defaultdict
from threading import Lock
from datetime import datetime
import inspect
import os
import requests

DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"
INNERMONO_PATH = "/home/triad/mitch/logs/innermono.log"

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

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls.__new__(cls)
                cls._instance.__init__()  # manual init on singleton
            return cls._instance

    def subscribe(self, event_type, callback):
        callback_id = f"{callback.__module__}.{callback.__name__}"
        if callback not in self.listeners[event_type]:
            self.listeners[event_type].append(callback)
            self.registry["subscriptions"][event_type].add(callback.__module__)
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
        preview = str(data)[:100].replace("\n", " ") if data else "None"

        # Register emitter
        emitter = self._infer_emitter_module()
        if emitter:
            self.registry["emits"][event_type].add(emitter)

        if DEBUG:
            print(f"[{ts}] [EventBus] EMIT: {event_type} -> {preview}")

        try:
            with open(INNERMONO_PATH, "a", encoding="utf-8") as f:
                f.write(f"{ts} [{event_type}] {preview}\n")
        except Exception as e:
            if DEBUG:
                print(f"[EventBus] Failed to write to innermono.log: {e}")

        for callback in self.listeners.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error handling '{event_type}': {e}")

        for callback in self.listeners.get("*", []):
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

    def get_registry(self):
        return self.registry

    def get_registered_handlers(self):
        return dict(self.listeners)

# === Singleton instance ===
event_bus = EventBus.get_instance()

# === Built-in listener for EMIT_SPEAK ===
def _log_emit_speak(data):
    if not data:
        return
    text = data.get("text")
    if text and data.get("source") != "status":
        try:
            requests.post("http://localhost:5000/emit_response", json={"text": text})
        except Exception as e:
            if DEBUG:
                print(f"[EventBus] Failed to forward EMIT_SPEAK to visual log: {e}")

event_bus.subscribe("EMIT_SPEAK", _log_emit_speak)
