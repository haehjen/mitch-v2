from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
import json
import os
import re
from core.config import MITCH_ROOT

DECISION_DATA_FILE = f"{MITCH_ROOT}/data/injections/decision_context.json"
logger = get_logger("decision_maker")

class DecisionMaker:
    def __init__(self):
        self.decision_context = self.load_decision_context()

    def load_decision_context(self):
        if os.path.exists(DECISION_DATA_FILE):
            with open(DECISION_DATA_FILE, 'r') as file:
                return json.load(file)
        return {}

    def save_decision_context(self):
        with open(DECISION_DATA_FILE, 'w') as file:
            json.dump(self.decision_context, file)

    def evaluate_decision(self, options):
        """Evaluate the best decision based on predefined criteria."""
        # Placeholder logic for decision evaluation
        # In a real implementation, this would be more complex
        best_option = max(options, key=lambda option: option.get('priority', 0))
        self.decision_context['last_decision'] = best_option
        self.save_decision_context()
        return best_option

    def handle_decision_request(self, data):
        if isinstance(data, str):
            text = data.strip()
            lower = text.lower()
            explicit = (
                "help me decide" in lower
                or "make a decision" in lower
                or "decide between" in lower
                or "which should i choose" in lower
            )
            if not explicit:
                logger.info("Decision intent ignored (not explicit decision phrasing).")
                return
            # Very light parser: "decide between A and B and C"
            m = re.search(r"decide between\s+(.+)", lower)
            if not m:
                event_bus.emit("EMIT_CHAT_REQUEST", {"prompt": text})
                return
            raw_opts = [x.strip(" ,.") for x in re.split(r"\band\b|,", m.group(1)) if x.strip(" ,.")]
            options = [{"label": o, "priority": 1} for o in raw_opts]
        else:
            payload = data if isinstance(data, dict) else {}
            options = payload.get('options', [])

        if options:
            best_option = self.evaluate_decision(options)
            # Emit the decision result
            event_bus.emit('DECISION_MADE', {'decision': best_option})
            # Log the decision
            logger.info(f"Decision made: {best_option}")


decision_maker = DecisionMaker()

def start_module(event_bus):
    event_bus.subscribe('REQUEST_DECISION', decision_maker.handle_decision_request)

    # Register intent for decision making
    IntentRegistry.register_intent(
        'make_decision',
        decision_maker.handle_decision_request,
        keywords=[
            'help me decide',
            'make a decision',
            'decide between',
            'which should i choose',
        ],
        objects=[],
        priority=30,
    )

    # Log module startup
    logger.info("DecisionMaker module started.")
