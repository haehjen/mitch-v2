import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_goal_tracker.log'

class AdaptiveGoalTracker:
    def __init__(self):
        self.goals = []
        self.load_goals()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_goals(self):
        try:
            with open('/home/triad/mitch/data/goals.json', 'r') as file:
                self.goals = json.load(file)
                self.log_action('Goals loaded successfully.')
        except FileNotFoundError:
            self.goals = []
            self.log_action('No existing goals file found, starting fresh.')

    def save_goals(self):
        with open('/home/triad/mitch/data/goals.json', 'w') as file:
            json.dump(self.goals, file)
            self.log_action('Goals saved successfully.')

    def update_goal_progress(self, goal_id, progress):
        for goal in self.goals:
            if goal['id'] == goal_id:
                goal['progress'] = progress
                self.log_action(f'Goal progress updated for {goal_id}: {progress}')
                self.provide_feedback(goal)
                break
        self.save_goals()

    def provide_feedback(self, goal):
        if goal['progress'] >= goal.get('target', 100):
            message = f"Congratulations! You've achieved your goal: {goal['description']}"
            event_bus.emit('EMIT_SPEAK', {'message': message})
            self.log_action(f'Emitted achievement message for goal: {goal}')
        else:
            message = f"Keep going! You're {goal['progress']}% towards your goal: {goal['description']}"
            event_bus.emit('EMIT_SPEAK', {'message': message})
            self.log_action(f'Emitted progress message for goal: {goal}')

    def start_tracking(self):
        self.log_action('Adaptive goal tracking started.')


def start_module(event_bus):
    tracker = AdaptiveGoalTracker()
    event_bus.subscribe('UPDATE_GOAL_PROGRESS', lambda data: tracker.update_goal_progress(data['id'], data['progress']))
    tracker.start_tracking()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
