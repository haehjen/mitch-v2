import re
from core.event_bus import event_bus
from difflib import SequenceMatcher

_last_input_text = None  # Prevent repeated GPT calls

THRESHOLD = 0.65  # Match confidence threshold

def compute_match_score(text, keywords, objects):
    score = 0
    for keyword in keywords:
        if keyword in text:
            score += 0.5
    for obj in objects:
        if obj in text:
            score += 0.5
    return score / (len(keywords) + len(objects))

def extract_numbers(text):
    return list(map(int, re.findall(r"\b\d+\b", text)))

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
                event_bus.emit("EMIT_SPEAK", {"text": f"Module {match.group(1)} has been updated."})
            ) if (match := re.match(r"edit module (\w+)\s+(.*)", text)) else None
        )(text)
    },
    "read_module": {
        "keywords": ["read", "show", "open", "display"],
        "objects": ["module", "script", "file"],
        "handler": lambda text: (
            lambda match: (
                event_bus.emit("EMIT_MODULE_READ", {"filename": f"core/{match.group(1)}.py" if match.group(1) in {"event_bus", "dispatcher", "peterjones"} else f"modules/{match.group(1)}.py"})
            ) if (match := re.match(r"read module (\w+)", text)) else None
        )(text)
    },
}

def match_intent(text):
    best_score = 0
    best_intent = None
    for intent, config in registered_intents.items():
        score = compute_match_score(text, config["keywords"], config["objects"])
        if score > best_score:
            best_score = score
            best_intent = intent
    return best_intent if best_score >= THRESHOLD else None

def handle_input(data):
    global _last_input_text
    text = data.get("text", "").lower().strip()

    if data.get("source") == "assistant":
        print("[Interpreter] Ignoring assistant-originated input")
        return

    if text == _last_input_text:
        print(f"[Interpreter] Ignoring duplicate prompt: '{text}'")
        return

    _last_input_text = text

    # === INTENT MATCHING ===
    intent = match_intent(text)
    if intent:
        handler = registered_intents[intent]["handler"]
        handler(text)
        return

    # === FALLBACK: detect code/module generation manually ===
    if re.search(r"\b(create|make|write|generate)\b.*\b(module|script|file|tool)\b", text):
        print("[Interpreter] Fallback matched: triggering create_module intent")
        registered_intents["create_module"]["handler"](text)
        return

    # === ESCALATE TO GPT ===
    if "?" in text or len(text.split()) < 4:
        print(f"[Interpreter] Escalating to GPT for ambiguous input: '{text}'")
    event_bus.emit("EMIT_CHAT_REQUEST", {"prompt": text})

def start_interpreter():
    print("[Interpreter] Online and listening for input events...")
    event_bus.subscribe("EMIT_INPUT_RECEIVED", handle_input)
