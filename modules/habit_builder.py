import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/habit_builder.log'
DATA_FILE = '/home/triad/mitch/data/habits.json'

class HabitBuilder:
    def __init__(self):
        self.habits = []
        self.load_habits()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_habits(self):
        try:
            with open(DATA_FILE, 'r') as file:
                self.habits = json.load(file)
                self.log_action('Habits loaded successfully.')
        except FileNotFoundError:
            self.habits = []
            self.log_action('No existing habit file found, starting fresh.')

    def save_habits(self):
        with open(DATA_FILE, 'w') as file:
            json.dump(self.habits, file)
            self.log_action('Habits saved successfully.')

    def add_habit(self, habit_data):
        self.habits.append(habit_data)
        self.save_habits()
        self.log_action(f'Habit added: {habit_data}')

    def remove_habit(self, habit_id):
        self.habits = [habit for habit in self.habits if habit['id'] != habit_id]
        self.save_habits()
        self.log_action(f'Habit removed: {habit_id}')

    def check_habits(self):
        current_time = datetime.now()
        for habit in self.habits:
            habit_time = datetime.fromisoformat(habit['time'])
            if current_time >= habit_time and not habit.get('completed_today', False):
                self.emit_habit_reminder(habit)

    def emit_habit_reminder(self, habit):
        reminder_message = f"It's time to work on your habit: {habit['description']}"
        event_bus.emit('EMIT_SPEAK', {'message': reminder_message})
        self.log_action(f'Reminder emitted for habit: {habit}')

    def mark_completed(self, habit_id):
        for habit in self.habits:
            if habit['id'] == habit_id:
                habit['completed_today'] = True
                self.save_habits()
                self.log_action(f'Habit marked as completed: {habit}')
                break

    def reset_daily_completion(self):
        for habit in self.habits:
            habit['completed_today'] = False
        self.save_habits()
        self.log_action('Daily completions reset for all habits.')

    def run_habit_checker(self):
        self.log_action('Habit checker started.')
        while True:
            self.check_habits()
            if datetime.now().hour == 0:  # Reset daily completion at midnight
                self.reset_daily_completion()
            sleep(60)  # Check every minute


def start_module(event_bus):
    habit_builder = HabitBuilder()
    Thread(target=habit_builder.run_habit_checker, daemon=True).start()

    event_bus.subscribe('ADD_HABIT', habit_builder.add_habit)
    event_bus.subscribe('REMOVE_HABIT', habit_builder.remove_habit)
    event_bus.subscribe('MARK_HABIT_COMPLETED', habit_builder.mark_completed)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
