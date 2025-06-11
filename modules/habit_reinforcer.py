import os
import json
import time
from datetime import datetime, timedelta
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class HabitReinforcer:
    def __init__(self):
        self.habit_completion_dates = {}

    def load_habit_data(self):
        """Loads habit completion data from the habit tracker."""
        # Assuming habit_tracker.py stores data in '/home/triad/mitch/data/habit_data.json'
        habit_data_path = '/home/triad/mitch/data/habit_data.json'
        if os.path.exists(habit_data_path):
            with open(habit_data_path, 'r') as file:
                self.habit_completion_dates = json.load(file)

    def reinforce_habit(self, event_data):
        """Reinforces the habit by checking completion and providing feedback."""
        habit_name = event_data.get('habit_name')
        if not habit_name:
            return

        today = datetime.now().date()
        last_completion_date = self.habit_completion_dates.get(habit_name)
        if last_completion_date:
            last_completion_date = datetime.strptime(last_completion_date, '%Y-%m-%d').date()

        if last_completion_date != today:
            self.habit_completion_dates[habit_name] = today.strftime('%Y-%m-%d')
            self._write_log(habit_name, today)
            self._emit_feedback(habit_name)

    def _write_log(self, habit_name, date):
        """Write the habit reinforcement activity to the log file."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'habit_name': habit_name,
            'completion_date': date.strftime('%Y-%m-%d')
        }
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')

    def _emit_feedback(self, habit_name):
        """Emit positive feedback for habit completion."""
        feedback_message = f"Great job on completing your habit: {habit_name} today! Keep it up!"
        event_bus.emit('EMIT_SPEAK', {
            'text': feedback_message,
            'token': str(time.time())
        })


def start_module(event_bus):
    habit_reinforcer = HabitReinforcer()
    habit_reinforcer.load_habit_data()
    event_bus.subscribe('EMIT_HABIT_COMPLETED', habit_reinforcer.reinforce_habit)
    
    print('Habit Reinforcer module started and listening for habit completion events.')
