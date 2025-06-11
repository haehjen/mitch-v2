import os
import json
from datetime import datetime
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class HabitAnalyzer:
    def __init__(self):
        self.habit_data = []

    def log_habit_analysis(self, analysis):
        """Log the habit analysis results."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'analysis': analysis
        }
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')

    def analyze_habits(self, event_data):
        """Analyze habits received from the habit_tracker module."""
        self.habit_data.append(event_data)
        # Simple analysis: identify most frequent habits
        habit_counts = {}
        for habit in event_data.get('habits', []):
            habit_name = habit.get('name')
            if habit_name not in habit_counts:
                habit_counts[habit_name] = 0
            habit_counts[habit_name] += 1

        # Determine most frequent habits
        most_common_habits = sorted(habit_counts.items(), key=lambda x: x[1], reverse=True)
        analysis_result = {
            'most_common_habits': most_common_habits,
            'total_habits': len(event_data.get('habits', []))
        }

        self.log_habit_analysis(analysis_result)

    def handle_habit_event(self, event_data):
        """Handle habit events emitted by the habit_tracker module."""
        self.analyze_habits(event_data)


def start_module(event_bus):
    habit_analyzer = HabitAnalyzer()
    event_bus.subscribe('EMIT_HABIT_DATA', habit_analyzer.handle_habit_event)
    print('Habit Analyzer module started and listening for habit data events.')
