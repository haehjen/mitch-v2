import os
import json
import logging
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ContextUpdater:
    def __init__(self):
        self.injections_dir = "/home/triad/mitch/data/injections"
        
    def handle_user_feedback(self, event_data):
        logging.info("Handling user feedback for context update.")
        self.process_feedback(event_data)
        
    def handle_system_update(self, event_data):
        logging.info("Handling system update for context adaptation.")
        self.process_system_update(event_data)

    def process_feedback(self, feedback):
        # Analyze feedback and prepare context update
        context_update = {
            "type": "feedback",
            "data": feedback
        }
        self.save_context_update(context_update)

    def process_system_update(self, update_info):
        # Analyze system update and prepare context update
        context_update = {
            "type": "system_update",
            "data": update_info
        }
        self.save_context_update(context_update)

    def save_context_update(self, context_update):
        try:
            output_path = os.path.join(self.injections_dir, "context_update.json")
            with open(output_path, "w") as file:
                json.dump(context_update, file)
            logging.info("Context update saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save context update: {str(e)}")


def start_module(event_bus):
    context_updater = ContextUpdater()
    event_bus.subscribe("user_feedback", context_updater.handle_user_feedback)
    event_bus.subscribe("system_update", context_updater.handle_system_update)
    logging.info("Context Updater module started and listening for updates.")
