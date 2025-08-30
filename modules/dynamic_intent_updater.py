import json
import os
from core.event_bus import event_bus

LOG_PATH = "/home/triad/mitch/logs/innermono.log"
INJECTION_PATH = "/home/triad/mitch/data/injections/dynamic_intent_update.json"


def log_action(message):
    with open(LOG_PATH, "a") as log_file:
        log_file.write(f"{message}\n")


def handle_intent_match_failed(event_data):
    """
    Handles the INTENT_MATCH_FAILED event, suggesting updates to intent matching.

    Args:
        event_data (dict): Data related to the failed intent match, including user input.
    """
    user_input = event_data.get('user_input', '')
    if not user_input:
        log_action("[dynamic_intent_updater] No user input found in event data.")
        return

    # Analyze the failed input and suggest an update
    log_action(f"[dynamic_intent_updater] Analyzing failed intent match for input: '{user_input}'")

    # For simplicity, just log the intent suggestion process
    suggestion = {
        "intent": "new_intent",  # Placeholder for actual intent logic
        "sample_inputs": [user_input]
    }

    # Save the suggestion to the injections folder
    with open(INJECTION_PATH, "w") as injection_file:
        json.dump(suggestion, injection_file)
    log_action(f"[dynamic_intent_updater] Suggested new intent based on input: '{user_input}'")


def start_module(event_bus):
    event_bus.subscribe('INTENT_MATCH_FAILED', handle_intent_match_failed)
    log_action("[dynamic_intent_updater] Module started and subscribed to INTENT_MATCH_FAILED event.")
