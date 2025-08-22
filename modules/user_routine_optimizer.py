import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_PATH = '/home/triad/mitch/logs/user_routine_optimizer.log'
DATA_PATH = '/home/triad/mitch/data/user_routine_data.json'

class UserRoutineOptimizer:
    def __init__(self):
        self.routine_data = self.load_data()

    def load_data(self):
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, 'r') as file:
                return json.load(file)
        return {}

    def save_data(self):
        with open(DATA_PATH, 'w') as file:
            json.dump(self.routine_data, file)

    def analyze_routine(self, event_data):
        user = event_data.get('user')
        task = event_data.get('task')
        timestamp = datetime.now().isoformat()

        if user not in self.routine_data:
            self.routine_data[user] = []

        self.routine_data[user].append({'task': task, 'timestamp': timestamp})
        self.save_data()

        self.log_action(f"Recorded task '{task}' for user '{user}' at {timestamp}.")

        if self.detect_inefficiency(user):
            suggestion = self.generate_suggestion(user)
            event_bus.emit('routine_optimization_suggestion', {'user': user, 'suggestion': suggestion})
            self.log_action(f"Suggested optimization for user '{user}': {suggestion}")

    def detect_inefficiency(self, user):
        # Simple inefficiency detection logic: if more than 3 tasks were done within an hour, suggest optimization.
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_tasks = [task for task in self.routine_data[user] if datetime.fromisoformat(task['timestamp']) > one_hour_ago]
        return len(recent_tasks) > 3

    def generate_suggestion(self, user):
        return "Consider batching similar tasks to save time."

    def log_action(self, message):
        with open(LOG_PATH, 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")

optimizer = UserRoutineOptimizer()

def start_module(event_bus):
    def handle_new_task(event_data):
        optimizer.analyze_routine(event_data)

    event_bus.subscribe('new_task_recorded', handle_new_task)
