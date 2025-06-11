import os
import json
import datetime
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class UserEngagementTracker:
    def __init__(self):
        self.interaction_start_time = None
        self.engagement_data = []

    def handle_interaction_start(self, event_data):
        """Handle the start of a user interaction by recording the start time."""
        self.interaction_start_time = datetime.datetime.now()

    def handle_interaction_end(self, event_data):
        """Handle the end of a user interaction by calculating duration and logging it."""
        if self.interaction_start_time is not None:
            end_time = datetime.datetime.now()
            duration = (end_time - self.interaction_start_time).total_seconds()
            engagement_entry = {
                'timestamp': end_time.isoformat(),
                'interaction_duration': duration
            }
            self.engagement_data.append(engagement_entry)
            self._write_log(engagement_entry)
            self.interaction_start_time = None

    def _write_log(self, data):
        """Write the engagement data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def summarize_engagement(self):
        """Summarize the logged engagement metrics."""
        total_duration = sum(entry['interaction_duration'] for entry in self.engagement_data)
        count = len(self.engagement_data)
        average_duration = total_duration / count if count > 0 else 0
        return {
            'total_interactions': count,
            'total_duration': total_duration,
            'average_duration': average_duration
        }

def start_module(event_bus):
    tracker = UserEngagementTracker()
    event_bus.subscribe('EMIT_INPUT_RECEIVED', tracker.handle_interaction_start)
    event_bus.subscribe('EMIT_SPEAK_END', tracker.handle_interaction_end)
    print('User Engagement Tracker module started and listening for interaction events.')
