import os
import json
import logging
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AutoIntentTrainer:
    def __init__(self):
        self.data_dir = "/home/triad/mitch/data/"
        self.injections_dir = os.path.join(self.data_dir, "injections")
        self.intent_data_file = os.path.join(self.data_dir, "intent_data.json")

    def update_intent_data(self, user_interaction_data):
        # Load existing intent data
        try:
            with open(self.intent_data_file, "r") as file:
                intent_data = json.load(file)
        except FileNotFoundError:
            intent_data = {}

        # Update intent data with new interactions
        for interaction in user_interaction_data:
            intent = interaction.get("intent")
            if intent:
                intent_data[intent] = intent_data.get(intent, 0) + 1

        # Save updated intent data
        with open(self.intent_data_file, "w") as file:
            json.dump(intent_data, file)
        logging.info("Intent data updated with recent user interactions.")

    def analyze_feedback(self, feedback_data):
        # Analyze feedback to refine intent recognition
        improvements = []
        for feedback in feedback_data:
            if "incorrect_intent" in feedback:
                improvements.append(feedback)

        if improvements:
            self.generate_improvement_suggestions(improvements)

    def generate_improvement_suggestions(self, improvements):
        # Generate suggestions to improve intent matching
        suggestion = {
            "intent_improvements": improvements
        }
        output_path = os.path.join(self.injections_dir, "intent_improvement_suggestions.json")
        with open(output_path, "w") as file:
            json.dump(suggestion, file)
        logging.info("Generated intent improvement suggestions.")

    def handle_user_interaction_event(self, event_data):
        # Handle user interaction events
        logging.info(f"Handling user interaction event: {event_data}")
        self.update_intent_data(event_data)

    def handle_feedback_event(self, event_data):
        # Handle feedback events
        logging.info(f"Handling feedback event: {event_data}")
        self.analyze_feedback(event_data)


def start_module(event_bus):
    trainer = AutoIntentTrainer()
    event_bus.subscribe("user_interaction", trainer.handle_user_interaction_event)
    event_bus.subscribe("user_feedback", trainer.handle_feedback_event)
    logging.info("Auto Intent Trainer module started and listening for user interaction and feedback events.")
