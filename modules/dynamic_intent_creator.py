import json
import os
from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("dynamic_intent_creator")

INJECTION_PATH = f"{MITCH_ROOT}/data/injections/dynamic_intents.json"
LOG_PATH = os.path.join(MITCH_ROOT, "logs", "innermono.log")
DYNAMIC_INTENT_AUTO_REGISTER = os.getenv("DYNAMIC_INTENT_AUTO_REGISTER", "false").lower() in ("1", "true", "yes", "on")

class DynamicIntentCreator:
    def __init__(self):
        self.known_phrases = self.load_known_phrases()

    def load_known_phrases(self):
        if os.path.exists(INJECTION_PATH):
            try:
                with open(INJECTION_PATH, "r") as file:
                    data = json.load(file)
                return data if isinstance(data, dict) else {}
            except Exception:
                logger.warning("dynamic_intents.json is malformed; resetting to empty mapping.")
                return {}
        return {}

    def save_known_phrases(self):
        with open(INJECTION_PATH, 'w') as file:
            json.dump(self.known_phrases, file)

    def process_unmatched_intent(self, data):
        if not DYNAMIC_INTENT_AUTO_REGISTER:
            return

        phrase = (data.get("text") or "").strip()
        if phrase and phrase not in self.known_phrases:
            # Only learn short imperative command-like phrases, not open-ended chat.
            if "?" in phrase or len(phrase.split()) > 8:
                return

            self.known_phrases[phrase] = "auto_detected_intent"
            self.save_known_phrases()
            self.register_new_intent(phrase)
            # Log the new intent
            logger.info(str(f"Registered new intent for phrase: {phrase}\n").rstrip("\n"))

    def register_new_intent(self, phrase):
        def handler(text):
            event_bus.emit('EMIT_CHAT_REQUEST', {'prompt': text})

        IntentRegistry.register_intent(
            'auto_detected_intent',
            handler,
            keywords=[phrase],
            objects=[]
        )


def start_module(event_bus):
    intent_creator = DynamicIntentCreator()
    event_bus.subscribe('INTENT_MATCH_FAILED', intent_creator.process_unmatched_intent)

    # Log module startup
    logger.info(
        str(
            f"DynamicIntentCreator module started. auto_register={'on' if DYNAMIC_INTENT_AUTO_REGISTER else 'off'}\n"
        ).rstrip("\n")
    )
