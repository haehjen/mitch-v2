import json
import time
from core.event_bus import event_bus
from core.peterjones import get_logger

class ProtestTracker:
    def __init__(self):
        self.protests_log = []
        self.logger = get_logger("protest_tracker")

    def check_for_protests(self, event_data):
        # Placeholder for web scraping or API call to gather protest data
        # This function should be implemented with actual data retrieval logic
        sample_protests = [
            {"location": "City Center", "description": "Large demonstration expected", "timestamp": time.time()},
            {"location": "Main Square", "description": "Peaceful protest ongoing", "timestamp": time.time()}
        ]
        self.protests_log.extend(sample_protests)
        self._log_to_file(sample_protests)
        self.emit_protest_updates(sample_protests)

    def _log_to_file(self, protests):
        for protest in protests:
            self.logger.info(f"Protest logged: {protest['description']} at {protest['location']}")

    def emit_protest_updates(self, protests):
        # Emit an event with the protest data for other modules to use
        event_bus.emit('EMIT_CHECK_PROTESTS', protests)

    def save_protest_data(self, protests):
        data = {
            'protests': protests,
            'timestamp': time.time()
        }
        with open('/home/triad/mitch/data/injections/protest_data.json', 'w') as data_file:
            json.dump(data, data_file)

protest_tracker = ProtestTracker()

def handle_heartbeat(event_data):
    protest_tracker.check_for_protests(event_data)
    if protest_tracker.protests_log:
        protest_tracker.save_protest_data(protest_tracker.protests_log)


def start_module(event_bus):
    event_bus.subscribe('ECHO_HEARTBEAT', handle_heartbeat)
    get_logger("protest_tracker").info("Protest Tracker module started.")
