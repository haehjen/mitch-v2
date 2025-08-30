import re
import time
from core.event_bus import event_bus, INNERMONO_PATH
from core.peterjones import get_logger
from core.event_registry import IntentRegistry

logger = get_logger("interpreter")

_last_input_text = None  # Prevent repeated GPT calls
THRESHOLD = 0.15  # Match confidence threshold

def extract_numbers(text):
    return list(map(int, re.findall(r"\b\d+\b", text)))

def extract_search_query(text):
    match = re.search(r"(?:search|google|look(?:\s*up)?|find)(?:\s+for)?\s+(.*)", text)
    return match.group(1).strip() if match else text.strip()

def extract_region_for_flights(text: str) -> str:
    m = re.search(r"(?:track\s+(?:flight|flights)|show\s+(?:flight|flights)|planes|aircraft)\s+([a-zA-Z][a-zA-Z\s\-]+)$", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:over|above|near|in|around)\s+([a-zA-Z][a-zA-Z\s\-]+)$", text)
    if m:
        return m.group(1).strip()
    tokens = [t for t in re.split(r"[^a-zA-Z\-]+", text) if t]
    if tokens:
        return tokens[-1].strip()
    return ""

def extract_location_from_text(text: str) -> str:
    m = re.search(r"(?:weather|forecast|conditions)\s+(in|at|for)\s+([a-zA-Z\s\-]+)", text)
    if m:
        return m.group(2).strip()
    tokens = [t for t in re.split(r"[^a-zA-Z\-]+", text) if t]
    return tokens[-1] if tokens else ""

def extract_route_coordinates(match) -> list:
    start = match.group(1).strip()
    end = match.group(2).strip()
    return [[-1.61, 54.97], [-2.24, 53.48]]  # Placeholder coordinates

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
    intent = IntentRegistry.match_intent(text)
    if intent:
        logger.info(f"Matched intent '{intent.name}' for input: '{text}'")
        intent.handler(text)
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