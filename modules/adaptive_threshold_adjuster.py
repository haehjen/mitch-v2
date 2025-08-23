import os
import json
import logging
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AdaptiveThresholdAdjuster:
    def __init__(self):
        self.thresholds_path = "/home/triad/mitch/data/thresholds.json"
        self.current_thresholds = self.load_thresholds()

    def load_thresholds(self):
        try:
            with open(self.thresholds_path, "r") as file:
                thresholds = json.load(file)
            return thresholds
        except FileNotFoundError:
            logging.warning("Thresholds file not found. Using default thresholds.")
            return {"cpu_usage": 80, "memory_usage": 80}

    def save_thresholds(self):
        with open(self.thresholds_path, "w") as file:
            json.dump(self.current_thresholds, file)
        logging.info("Thresholds updated and saved.")

    def adjust_thresholds(self, event_data):
        logging.info(f"Adjusting thresholds based on event data: {event_data}")
        # Example logic to adjust thresholds
        cpu_usage = event_data.get("cpu_usage", 0)
        memory_usage = event_data.get("memory_usage", 0)

        # Simple logic: if usage is consistently high, increase the threshold
        if cpu_usage > self.current_thresholds["cpu_usage"]:
            self.current_thresholds["cpu_usage"] += 5
        if memory_usage > self.current_thresholds["memory_usage"]:
            self.current_thresholds["memory_usage"] += 5

        self.save_thresholds()

    def handle_system_health_event(self, event_data):
        self.adjust_thresholds(event_data)


def start_module(event_bus):
    threshold_adjuster = AdaptiveThresholdAdjuster()
    event_bus.subscribe("system_health_status", threshold_adjuster.handle_system_health_event)
    logging.info("Adaptive Threshold Adjuster module started and listening for system health events.")
