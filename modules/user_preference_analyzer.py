import os
import json
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class UserPreferenceAnalyzer:
    def __init__(self):
        self.preferences = {}

    def log_user_interaction(self, event_data):
        """Log user interaction to track preferences."""
        interaction_type = event_data.get('interaction_type')
        if interaction_type not in self.preferences:
            self.preferences[interaction_type] = 0
        self.preferences[interaction_type] += 1
        self._write_log({
            'interaction_type': interaction_type,
            'count': self.preferences[interaction_type]
        })

    def _write_log(self, data):
        """Write the preference data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def summarize_preferences(self):
        """Summarize the user preferences."""
        return self.preferences

    def handle_interaction_event(self, event_data):
        """Handle interaction events emitted by other modules."""
        self.log_user_interaction(event_data)


def start_module(event_bus):
    user_preference_analyzer = UserPreferenceAnalyzer()
    event_bus.subscribe('USER_INTERACTION', user_preference_analyzer.handle_interaction_event)
    
    print('User Preference Analyzer module started and listening for user interaction events.')
