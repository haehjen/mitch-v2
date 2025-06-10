import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/activity_recognition.log'

class ActivityRecognition:
    def __init__(self):
        self.activities = []

    def log_activity(self, activity_data):
        """Log the recognized activity."""
        timestamp = datetime.now().isoformat()
        activity_entry = {
            'timestamp': timestamp,
            'activity': activity_data.get('activity'),
            'context': activity_data.get('context')
        }
        self.activities.append(activity_entry)
        self._write_log(activity_entry)

    def _write_log(self, data):
        """Write the activity data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def analyze_interaction(self, event_data):
        """Analyze interaction data to recognize activities."""
        # Placeholder logic for activity recognition
        # This would typically involve more complex analysis
        interaction_type = event_data.get('interaction_type')
        context = event_data.get('context')

        if interaction_type == 'typing':
            activity_data = {'activity': 'Working', 'context': context}
        elif interaction_type == 'speaking':
            activity_data = {'activity': 'Meeting', 'context': context}
        else:
            activity_data = {'activity': 'Idle', 'context': context}

        self.log_activity(activity_data)

    def handle_environment_change(self, event_data):
        """Handle environmental changes that may influence activity recognition."""
        # Placeholder for reacting to environmental changes
        # This could be expanded with more detailed context analysis
        temperature = event_data.get('temperature')
        if temperature > 30:
            activity_data = {'activity': 'Taking a Break', 'context': 'High Temperature'}
            self.log_activity(activity_data)


def start_module(event_bus):
    activity_recognition = ActivityRecognition()
    event_bus.subscribe('USER_INTERACTION', activity_recognition.analyze_interaction)
    event_bus.subscribe('ENVIRONMENT_CHANGE', activity_recognition.handle_environment_change)
    
    print('Activity Recognition module started and listening for user interaction and environment change events.')
