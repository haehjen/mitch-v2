import json
from pathlib import Path

from core.config import MITCH_ROOT
from core.event_registry import IntentRegistry
from core.peterjones import get_logger

logger = get_logger("user_feedback_collector")
FEEDBACK_FILE = Path(MITCH_ROOT) / "data" / "user_feedback.jsonl"
INJECTION_FILE = Path(MITCH_ROOT) / "data" / "injections" / "user_feedback_injection.json"

class UserFeedbackCollector:
    def __init__(self):
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        FEEDBACK_FILE.touch(exist_ok=True)

    def collect_feedback(self, feedback_data):
        with FEEDBACK_FILE.open("a", encoding="utf-8") as file:
            json.dump(feedback_data, file)
            file.write("\n")

        logger.info(f"Collected user feedback: {feedback_data}")

        event_bus.emit("USER_FEEDBACK_COLLECTED", feedback_data)

user_feedback_collector = UserFeedbackCollector()

def handle_user_feedback_event(data):
    user_feedback_collector.collect_feedback(data)

    context_change = {
        "feedback": data
    }
    INJECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    INJECTION_FILE.write_text(json.dumps(context_change, indent=2), encoding="utf-8")


def start_module(event_bus):
    event_bus.subscribe("USER_FEEDBACK_EVENT", handle_user_feedback_event)

    # Register intent for collecting user feedback
    IntentRegistry.register_intent(
        "provide_feedback",
        handle_user_feedback_event,
        keywords=["feedback", "response", "improve", "better"],
        objects=[],
    )

    logger.info("UserFeedbackCollector module started.")
