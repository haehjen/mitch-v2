import os
import json
import datetime
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class HabitTracker:
    def __init__(self):
        self.habits = {}

    def log_habit(self, event_data):
        """Log the habit from event_data."""
        timestamp = datetime.datetime.now().isoformat()
        habit_name = event_data.get('habit_name')
        if habit_name not in self.habits:
            self.habits[habit_name] = []
        self.habits[habit_name].append(timestamp)
        self._write_log(habit_name, timestamp)

    def _write_log(self, habit_name, timestamp):
        """Write the habit data to the log file."""
        log_entry = {
            'timestamp': timestamp,
            'habit_name': habit_name
        }
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')

    def summarize_habits(self):
        """Summarize the logged habits."""
        summary = {}
        for habit, timestamps in self.habits.items():
            summary[habit] = len(timestamps)
        return summary

    def handle_habit_event(self, event_data):
        """Handle habit events emitted by other modules."""
        self.log_habit(event_data)


def start_module(event_bus):
    habit_tracker = HabitTracker()
    event_bus.subscribe('EMIT_HABIT_EVENT', habit_tracker.handle_habit_event)
    
    print('Habit Tracker module started and listening for habit events.')
