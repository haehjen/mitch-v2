import os
import json
import logging
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SelfImprovementRecommender:
    def __init__(self):
        self.data_dir = "/home/triad/mitch/data/"
        self.injections_dir = os.path.join(self.data_dir, "injections")
        self.log_path = "/home/triad/mitch/logs/innermono.log"

    def analyze_logs(self):
        # Read the innermono.log for insights
        try:
            with open(self.log_path, "r") as file:
                logs = file.readlines()
            
            improvements = []
            for line in logs:
                if "ERROR" in line or "FIX" in line:
                    improvements.append(line.strip())

            return improvements
        except FileNotFoundError:
            logging.error("Log file not found.")
            return []

    def suggest_improvements(self):
        # Analyze logs for potential improvements
        improvements = self.analyze_logs()
        if improvements:
            suggestion = {
                "suggestions": improvements
            }
            output_path = os.path.join(self.injections_dir, "improvement_suggestions.json")
            with open(output_path, "w") as file:
                json.dump(suggestion, file)
            logging.info("Improvement suggestions generated and saved.")

    def handle_feedback_event(self, event_data):
        # Handle feedback received
        logging.info(f"Received feedback: {event_data}")
        # Process feedback for improvements
        self.suggest_improvements()


def start_module(event_bus):
    recommender = SelfImprovementRecommender()
    event_bus.subscribe("user_feedback", recommender.handle_feedback_event)
    logging.info("Self Improvement Recommender module started and listening for feedback events.")