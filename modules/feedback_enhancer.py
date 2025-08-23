import os
import json
import logging
from datetime import datetime
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FeedbackEnhancer:
    def __init__(self):
        self.data_dir = "/home/triad/mitch/data/"
        self.feedback_dir = os.path.join(self.data_dir, "injections")
        self.feedback_file = os.path.join(self.feedback_dir, "enhanced_feedback.json")

    def handle_user_feedback(self, event_data):
        # Log the reception of feedback
        logging.info(f"Received user feedback: {event_data}")

        # Analyze and categorize feedback
        categorized_feedback = self.categorize_feedback(event_data)
        
        # Save categorized feedback
        self.save_feedback(categorized_feedback)

    def categorize_feedback(self, feedback):
        # Simple categorization logic (can be expanded)
        if "error" in feedback.lower():
            category = "Error"
        elif "improve" in feedback.lower():
            category = "Improvement"
        else:
            category = "General"

        # Create feedback entry
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback,
            "category": category
        }

        return feedback_entry

    def save_feedback(self, feedback_entry):
        # Ensure directory exists
        if not os.path.exists(self.feedback_dir):
            os.makedirs(self.feedback_dir)

        # Load existing feedback
        if os.path.exists(self.feedback_file):
            with open(self.feedback_file, "r") as file:
                feedback_data = json.load(file)
        else:
            feedback_data = []

        # Append new feedback
        feedback_data.append(feedback_entry)

        # Save updated feedback data
        with open(self.feedback_file, "w") as file:
            json.dump(feedback_data, file, indent=4)

        logging.info("Enhanced feedback saved successfully.")


def start_module(event_bus):
    enhancer = FeedbackEnhancer()
    event_bus.subscribe("user_feedback", enhancer.handle_user_feedback)
    logging.info("Feedback Enhancer module started and listening for user feedback events.")
