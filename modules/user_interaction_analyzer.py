import os
import json
from datetime import datetime
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class UserInteractionAnalyzer:
    def __init__(self):
        self.interactions = []

    def log_interaction(self, event_data):
        """Log the user interaction data."""
        timestamp = datetime.now().isoformat()
        interaction_data = {
            'timestamp': timestamp,
            'interaction_type': event_data.get('interaction_type'),
            'duration': event_data.get('duration')
        }
        self.interactions.append(interaction_data)
        self._write_log(interaction_data)

    def _write_log(self, data):
        """Write the interaction data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def analyze_interactions(self):
        """Analyze the logged interactions to identify patterns."""
        summary = {}
        for entry in self.interactions:
            interaction_type = entry['interaction_type']
            if interaction_type not in summary:
                summary[interaction_type] = 0
            summary[interaction_type] += 1
        return summary

    def handle_interaction_event(self, event_data):
        """Handle interaction events emitted by other modules."""
        self.log_interaction(event_data)
        # Emit a summary of interactions after each event
        interaction_summary = self.analyze_interactions()
        event_bus.emit('INTERACTION_SUMMARY', interaction_summary)


def start_module(event_bus):
    analyzer = UserInteractionAnalyzer()
    event_bus.subscribe('USER_INTERACTION', analyzer.handle_interaction_event)
    
    print('User Interaction Analyzer module started and listening for user interaction events.')
