from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
import json
import os

class HabitTracker:
    def __init__(self):
        self.habits_file = '/home/triad/mitch/data/habits.json'
        self.load_habits()
        self.logger = get_logger("habit_tracker")

    def load_habits(self):
        if os.path.exists(self.habits_file):
            with open(self.habits_file, 'r') as file:
                self.habits = json.load(file)
        else:
            self.habits = {}

    def save_habits(self):
        with open(self.habits_file, 'w') as file:
            json.dump(self.habits, file)

    def log_habit(self, habit_name, status):
        if habit_name not in self.habits:
            self.habits[habit_name] = {'status': status, 'history': []}
        self.habits[habit_name]['history'].append(status)
        self.save_habits()
        self.log_action(f"Habit logged: {habit_name} - {status}")

    def set_goal(self, habit_name, goal):
        if habit_name in self.habits:
            self.habits[habit_name]['goal'] = goal
            self.save_habits()
            self.log_action(f"Goal set for {habit_name}: {goal}")
        else:
            self.log_action(f"Failed to set goal: Habit {habit_name} not found.")

    def get_progress(self, habit_name):
        if habit_name in self.habits:
            history = self.habits[habit_name]['history']
            goal = self.habits[habit_name].get('goal', 0)
            progress = len([s for s in history if s])
            self.log_action(f"Progress for {habit_name}: {progress}/{goal}")
            return progress, goal
        else:
            self.log_action(f"Failed to get progress: Habit {habit_name} not found.")
            return None, None

    def log_action(self, message):
        self.logger.info(message)


def start_module(event_bus):
    tracker = HabitTracker()

    def handle_log_habit(data):
        habit_name = data.get('habit_name')
        status = data.get('status')
        tracker.log_habit(habit_name, status)

    def handle_set_goal(data):
        habit_name = data.get('habit_name')
        goal = data.get('goal')
        tracker.set_goal(habit_name, goal)

    def handle_get_progress(data):
        habit_name = data.get('habit_name')
        progress, goal = tracker.get_progress(habit_name)
        event_bus.emit('HABIT_PROGRESS', {
            'habit_name': habit_name,
            'progress': progress,
            'goal': goal
        })

    event_bus.subscribe('LOG_HABIT', handle_log_habit)
    event_bus.subscribe('SET_HABIT_GOAL', handle_set_goal)
    event_bus.subscribe('GET_HABIT_PROGRESS', handle_get_progress)

    IntentRegistry.register_intent(
        'log_habit',
        handle_log_habit,
        keywords=['log', 'record', 'habit'],
        objects=['habit_name', 'status']
    )

    IntentRegistry.register_intent(
        'set_habit_goal',
        handle_set_goal,
        keywords=['set', 'goal', 'habit'],
        objects=['habit_name', 'goal']
    )

    IntentRegistry.register_intent(
        'get_habit_progress',
        handle_get_progress,
        keywords=['progress', 'status', 'habit'],
        objects=['habit_name']
    )
