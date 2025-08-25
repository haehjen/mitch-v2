import os
import re
import time
import json
from core.event_bus import event_bus, INNERMONO_PATH
from core.peterjones import get_logger
from difflib import SequenceMatcher

logger = get_logger("interpreter")

_last_input_text = None  # Prevent repeated GPT calls
THRESHOLD = 0.15  # Match confidence threshold

def compute_match_score(text, keywords, objects):
    score = 0
    for keyword in keywords:
        if keyword in text:
            score += 0.5
    for obj in objects:
        if obj in text:
            score += 0.5
    return score / (len(keywords) + len(objects)) if (keywords or objects) else 0

def extract_numbers(text):
    return list(map(int, re.findall(r"\b\d+\b", text)))

def extract_search_query(text):
    match = re.search(r"(?:search|google|look(?:\s*up)?|find)(?:\s+for)?\s+(.*)", text)
    return match.group(1).strip() if match else text.strip()

# --- helper for flights ---
# Accepts things like:
# - "track flights newcastle"
# - "are there any planes over london"
# - "show aircraft near manchester"
def extract_region_for_flights(text: str) -> str:
    # 1) direct "track flights <region>"
    m = re.search(r"(?:track\s+(?:flight|flights)|show\s+(?:flight|flights)|planes|aircraft)\s+([a-zA-Z][a-zA-Z\s\-]+)$", text)
    if m:
        return m.group(1).strip()

    # 2) preposition form "... over/above/near/in/around <region>"
    m = re.search(r"(?:over|above|near|in|around)\s+([a-zA-Z][a-zA-Z\s\-]+)$", text)
    if m:
        return m.group(1).strip()

    # 3) last token fallback (single word region at the end)
    tokens = [t for t in re.split(r"[^a-zA-Z\-]+", text) if t]
    if tokens:
        return tokens[-1].strip()
    return ""

# Extract rough location name from weather request
def extract_location_from_text(text: str) -> str:
    m = re.search(r"(?:weather|forecast|conditions)\s+(in|at|for)\s+([a-zA-Z\s\-]+)", text)
    if m:
        return m.group(2).strip()
    # fallback: last place-like word
    tokens = [t for t in re.split(r"[^a-zA-Z\-]+", text) if t]
    return tokens[-1] if tokens else ""

# Dummy route extraction — replace with real geocoder later
def extract_route_coordinates(match) -> list:
    start = match.group(1).strip()
    end = match.group(2).strip()
    # You could call a geocoding API here to convert to [lon, lat]
    # Placeholder coordinates for now:
    return [[-1.61, 54.97], [-2.24, 53.48]]  # Newcastle to Manchester

# === INTENT REGISTRY ===
registered_intents = {
    "launch_drone": {
        "keywords": ["launch", "deploy", "send", "activate"],
        "objects": ["drone", "unit"],
        "handler": lambda text: event_bus.emit("EMIT_USER_INTENT", {
            "intent": "launch_drone",
            "params": {"drone_ids": extract_numbers(text) or [1]}
        })
    },
    "describe_scene": {
        "keywords": ["describe", "what", "can", "see"],
        "objects": ["room", "scene", "view"],
        "handler": lambda text: event_bus.emit("EMIT_USER_INTENT", {
            "intent": "describe_scene",
            "params": {}
        })
    },
    "create_module": {
        "keywords": ["create", "make", "generate", "write"],
        "objects": ["module", "script", "file", "tool", "module name", "python file"],
        "handler": lambda text: event_bus.emit("EMIT_MODULE_REQUEST", {
            "prompt": text
        })
    },
    "edit_module": {
        "keywords": ["edit", "modify", "update"],
        "objects": ["module", "script", "file"],
        "handler": lambda text: (
            lambda match: (
                event_bus.emit("EMIT_MODULE_EDIT", {"filename": f"modules/{match.group(1)}.py", "content": match.group(2)}),
                event_bus.emit("EMIT_SPEAK", {
                    "text": f"Module {match.group(1)} has been updated.",
                    "token": str(time.time())
                })
            ) if (match := re.match(r"edit module (\w+)\s+(.*)", text)) else None
        )(text)
    },
    "read_module": {
        "keywords": ["read", "show", "open", "display"],
        "objects": ["module", "script", "file"],
        "handler": lambda text: (
            lambda match: (
                event_bus.emit("EMIT_MODULE_READ", {
                    "filename": f"core/{match.group(1)}.py" if match.group(1) in {"event_bus", "dispatcher", "peterjones"} else f"modules/{match.group(1)}.py"
                })
            ) if (match := re.match(r"read module (\w+)", text)) else None
        )(text)
    },
    "web_search": {
        "keywords": ["search", "google", "look", "find"],
        "objects": ["web", "internet"],
        "handler": lambda text: event_bus.emit("EMIT_WEB_SEARCH", {"query": extract_search_query(text)})
    },
    # --- NEW: track flights intent ---
    "track_flights": {
        "keywords": ["track", "planes", "plane", "flights", "flight", "aircraft", "traffic"],
        "objects": ["over", "above", "near", "in", "around"],  # language cues
        "handler": lambda text: event_bus.emit("EMIT_TRACK_FLIGHTS", {
            "region": extract_region_for_flights(text) or "newcastle"  # sensible default
        })
    },
    "read_log": {
        "keywords": ["read", "show", "check", "display"],
        "objects": ["log", "logfile", "modules_created", "created modules", "log file"],
        "handler": lambda text: event_bus.emit("EMIT_READ_LOG", {
            "path": INNERMONO_PATH
        })
    },
    "get_weather": {
    "keywords": ["weather", "forecast", "rain", "temperature", "conditions"],
    "objects": ["today", "outside", "like", "right now", "Tommorrow", "in", "at", "for"],
    "handler": lambda text: event_bus.emit("GET_WEATHER", {
        "location": extract_location_from_text(text) or "newcastle"
    })
    },
    "plan_route": {
    "keywords": ["route", "directions", "navigate", "travel", "get"],
    "objects": ["from", "to", "via", "waypoint"],
    "handler": lambda text: (
        lambda match: event_bus.emit("PLAN_ROUTE", {
            "coords": extract_route_coordinates(match)
        }) if (match := re.search(r"from (.+?) to (.+)", text)) else event_bus.emit("EMIT_USER_INTENT", {
            "intent": "plan_route",
            "params": {"text": text}
        })
    )(text)
   },
}

def match_intent(text):
    # 1. Exact prefix match on intent name (e.g., "web_search latest ai model releases")
    for intent_name in registered_intents:
        if text.startswith(intent_name):
            logger.debug(f"Matched intent via direct prefix: {intent_name}")
            return intent_name

    # 2. Exact keyword pattern match (mostly for dynamic intents)
    for intent_name, config in registered_intents.items():
        pattern = ' '.join(config.get("keywords", []))
        if pattern and pattern.strip().lower() == text.strip().lower():
            logger.debug(f"Matched intent via exact pattern: {intent_name}")
            return intent_name

    # 3. Scored keyword/object match
    best_score = 0
    best_intent = None
    for intent_name, config in registered_intents.items():
        score = compute_match_score(text, config["keywords"], config["objects"])
        logger.debug(f"[Intent Scoring] {intent_name}: {score:.2f}")
        if score > best_score:
            best_score = score
            best_intent = intent_name

    return best_intent if best_score >= THRESHOLD else None

def handle_input(data):
    global _last_input_text
    text = data.get("text", "").lower().strip()

    if data.get("source") == "assistant":
        logger.debug("Ignoring assistant-originated input")
        return

    if text == _last_input_text:
        logger.debug(f"Ignoring duplicate prompt: '{text}'")
        return

    _last_input_text = text

    # === INTENT MATCHING ===
    intent = match_intent(text)
    if intent:
        logger.info(f"Matched intent '{intent}' for input: '{text}'")
        handler = registered_intents[intent]["handler"]
        handler(text)
        return

    # === FALLBACK: detect code/module generation manually ===
    if re.search(r"\b(create|make|write|generate)\b.*\b(module|script|file|tool)\b", text):
        logger.info("Fallback matched: triggering create_module intent")
        registered_intents["create_module"]["handler"](text)
        return

    # === ESCALATE TO GPT ===
    if "?" in text or len(text.split()) < 4:
        logger.debug(f"Escalating to GPT for ambiguous input: '{text}'")
    event_bus.emit("EMIT_CHAT_REQUEST", {"prompt": text})

def start_interpreter():
    logger.info("Interpreter online and listening for input events...")

    # Standard user input
    event_bus.subscribe("EMIT_INPUT_RECEIVED", handle_input)

    # HouseCore remote input from Pi
    def transform_housecore_input(event):
        transcript = event.get("transcript")
        if transcript:
            logger.debug(f"Transforming HOUSECORE_INPUT to EMIT_INPUT_RECEIVED: {transcript}")
            event_bus.emit("EMIT_INPUT_RECEIVED", {
                "text": transcript,
                "source": "HouseCore"
            })

    event_bus.subscribe("HOUSECORE_INPUT", transform_housecore_input)

    # === DYNAMIC INTENTS LOADER ===
    dynamic_path = "/home/triad/mitch/data/injections/dynamic_intents.json"
    if os.path.exists(dynamic_path):
        try:
            with open(dynamic_path, "r") as f:
                data = json.load(f)
                for intent_obj in data.get("intents", []):
                    intent_name = intent_obj.get("intent")
                    pattern = intent_obj.get("pattern")
                    action = intent_obj.get("action")

                    if not intent_name or not action:
                        logger.warning(f"Skipping malformed dynamic intent: {intent_obj}")
                        continue

                    logger.info(f"Registering dynamic intent: {intent_name} -> {action}")

                    def handler_factory(intent_name, action):
                        def handler(text):
                            logger.info(f"Dynamic intent '{intent_name}' matched. Dispatching to action '{action}'.")
                            event_bus.emit("EMIT_USER_INTENT", {
                                "intent": action,
                                "params": {"text": text}
                            })
                        return handler

                    # Dynamic intents will still be scored unless matched exactly
                    registered_intents[intent_name] = {
                        "keywords": pattern.split(),
                        "objects": [],
                        "handler": handler_factory(intent_name, action)
                    }

        except Exception as e:
            logger.error(f"Failed to load dynamic intents: {e}")
