import os
import json
import logging
from collections import defaultdict
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UserInteractionAnalyzer:
    def __init__(self):
        self.interaction_data = defaultdict(int)
        self.output_path = "/home/triad/mitch/data/injections/user_interaction_patterns.json"

    def analyze_interaction(self, event_data):
        # Increment the count for the type of interaction
        interaction_type = event_data.get('intent', 'unknown')
        self.interaction_data[interaction_type] += 1
        logging.info(f"Recorded interaction: {interaction_type}")

    def generate_report(self):
        # Generate a report of interaction patterns
        if self.interaction_data:
            with open(self.output_path, "w") as file:
                json.dump(self.interaction_data, file)
            logging.info("User interaction patterns saved.")

    def handle_shutdown(self, data):
        # On shutdown, save the interaction patterns
        self.generate_report()


def start_module(event_bus):
    analyzer = UserInteractionAnalyzer()
    event_bus.subscribe('user_interaction', analyzer.analyze_interaction)
    event_bus.subscribe('SHUTDOWN', analyzer.handle_shutdown)
    logging.info("User Interaction Analyzer module started and listening for events.")
