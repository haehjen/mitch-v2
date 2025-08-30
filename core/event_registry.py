import os
import json
import re
from collections import defaultdict
from datetime import datetime
from threading import Lock
from core.config import MITCH_ROOT

REGISTRY_LOG_PATH = os.path.join(MITCH_ROOT, "data/injections", "event_registry.json")


class EventRegistry:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self.registry = defaultdict(lambda: {"emitters": set(), "subscribers": set()})
        self.load_registry()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def record_emit(self, event_name, source):
        self.registry[event_name]["emitters"].add(source)
        self.save_registry()

    def record_subscribe(self, event_name, subscriber):
        self.registry[event_name]["subscribers"].add(subscriber)
        self.save_registry()

    def get_all_events(self):
        return list(self.registry.keys())

    def get_emitters_for(self, event_name):
        return list(self.registry[event_name]["emitters"])

    def get_subscribers_for(self, event_name):
        return list(self.registry[event_name]["subscribers"])

    def save_registry(self):
        with open(REGISTRY_LOG_PATH, "w") as f:
            json.dump({k: {
                "emitters": list(v["emitters"]),
                "subscribers": list(v["subscribers"])
            } for k, v in self.registry.items()}, f, indent=2)

    def load_registry(self):
        if os.path.exists(REGISTRY_LOG_PATH):
            try:
                with open(REGISTRY_LOG_PATH, "r") as f:
                    data = json.load(f)
                    for event, info in data.items():
                        self.registry[event]["emitters"].update(info.get("emitters", []))
                        self.registry[event]["subscribers"].update(info.get("subscribers", []))
            except Exception as e:
                print(f"[EventRegistry] Failed to load registry: {e}")


class Intent:
    def __init__(self, name, handler, keywords=None, objects=None):
        self.name = name
        self.handler = handler
        self.keywords = keywords or []
        self.objects = objects or []

    def matches(self, text):
        text = text.lower().strip()
        if len(text.split()) < 3 or not any(c.isalpha() for c in text):
            return False
        return any(kw in text for kw in self.keywords)


class IntentRegistry:
    intents = []

    @classmethod
    def register_intent(cls, name, handler, keywords=None, objects=None):
        cls.intents.append(Intent(name, handler, keywords, objects))

    @classmethod
    def match_intent(cls, text):
        for intent in cls.intents:
            if intent.matches(text):
                return intent
        return None


# === Example Intent Registrations ===
IntentRegistry.register_intent(
    "launch_drone",
    lambda text: print("Launching drone..."),
    keywords=["launch", "drone"]
)

IntentRegistry.register_intent(
    "get_weather",
    lambda text: print("Fetching weather..."),
    keywords=["weather", "forecast"]
)
