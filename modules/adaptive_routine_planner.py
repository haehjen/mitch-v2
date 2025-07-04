import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_routine_planner.log'

class AdaptiveRoutinePlanner:
    def __init__(self):
        self.routines = []
        self.load_routines()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_routines(self):
        try:
            with open('/home/triad/mitch/data/routines.json', 'r') as file:
                self.routines = json.load(file)
                self.log_action('Routines loaded successfully.')
        except FileNotFoundError:
            self.routines = []
            self.log_action('No existing routine file found, starting fresh.')

    def save_routines(self):
        with open('/home/triad/mitch/data/routines.json', 'w') as file:
            json.dump(self.routines, file)
            self.log_action('Routines saved successfully.')

    def generate_routine(self, user_data):
        # Example of routine generation logic
        # Here we would analyze user's habits, goals, and schedule
        new_routine = {
            'date': datetime.now().date().isoformat(),
            'tasks': [
                {'time': '08:00', 'activity': 'Morning Exercise'},
                {'time': '09:00', 'activity': 'Work on Project A'},
                {'time': '12:00', 'activity': 'Lunch Break'},
                {'time': '13:00', 'activity': 'Attend Meeting'},
                {'time': '15:00', 'activity': 'Review Goals'},
                {'time': '18:00', 'activity': 'Evening Walk'}
            ]
        }
        self.routines.append(new_routine)
        self.save_routines()
        self.emit_routine_update(new_routine)
        self.log_action(f'New routine generated: {new_routine}')

    def emit_routine_update(self, routine):
        event_bus.emit('EMIT_ROUTINE_UPDATE', {'routine': routine})

    def handle_user_data_event(self, event_data):
        # Handle incoming user data to generate new routines
        self.generate_routine(event_data)


def start_module(event_bus):
    routine_planner = AdaptiveRoutinePlanner()
    event_bus.subscribe('USER_DATA_EVENT', routine_planner.handle_user_data_event)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
