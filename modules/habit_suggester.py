import os
import json
from datetime import datetime
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class HabitSuggester:
    def __init__(self):
        self.habit_suggestions = []

    def analyze_habits(self, interaction_data):
        """Analyze past interactions to suggest new habits or modifications."""
        # Example: Analyze interaction data to suggest habits
        # This is a placeholder logic for demonstration
        user_activity = interaction_data.get('user_activity')
        if user_activity == 'sedentary':
            suggestion = 'Consider taking short walks every hour.'
            self.habit_suggestions.append(suggestion)
            self._write_log({'suggestion': suggestion})

    def _write_log(self, data):
        """Write the suggestion to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def handle_interaction_event(self, event_data):
        """Handle interaction events emitted by other modules."""
        self.analyze_habits(event_data)


def start_module(event_bus):
    habit_suggester = HabitSuggester()
    event_bus.subscribe('EMIT_USER_ACTIVITY', habit_suggester.handle_interaction_event)
    
    print('Habit Suggester module started and listening for user activity events.')
