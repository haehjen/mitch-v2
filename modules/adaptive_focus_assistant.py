import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_focus_assistant.log'

class AdaptiveFocusAssistant:
    def __init__(self):
        self.last_interaction_time = datetime.now()
        self.default_reminder_interval = timedelta(minutes=15)
        self.adaptive_interval = self.default_reminder_interval
        self.load_user_patterns()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_user_patterns(self):
        try:
            with open('/home/triad/mitch/data/user_focus_patterns.json', 'r') as file:
                self.user_patterns = json.load(file)
                self.log_action('User patterns loaded successfully.')
        except FileNotFoundError:
            self.user_patterns = {}
            self.log_action('No existing user patterns file found, starting fresh.')

    def save_user_patterns(self):
        with open('/home/triad/mitch/data/user_focus_patterns.json', 'w') as file:
            json.dump(self.user_patterns, file)
            self.log_action('User patterns saved successfully.')

    def update_focus_patterns(self, event_data):
        # Logic to update user patterns based on interaction events
        current_hour = datetime.now().hour
        if current_hour not in self.user_patterns:
            self.user_patterns[current_hour] = {'interactions': 0, 'reminders_issued': 0}
        self.user_patterns[current_hour]['interactions'] += 1
        self.save_user_patterns()
        self.log_action(f'User pattern updated for hour {current_hour}.')

    def handle_interaction_event(self, event_data):
        self.last_interaction_time = datetime.now()
        self.update_focus_patterns(event_data)
        self.log_action('Interaction event received, resetting timer.')

    def adjust_reminder_interval(self):
        current_hour = datetime.now().hour
        if current_hour in self.user_patterns:
            interaction_count = self.user_patterns[current_hour].get('interactions', 0)
            reminders_issued = self.user_patterns[current_hour].get('reminders_issued', 0)
            if interaction_count > reminders_issued:
                self.adaptive_interval = timedelta(minutes=10)  # More frequent reminders
            else:
                self.adaptive_interval = timedelta(minutes=20)  # Less frequent reminders
        else:
            self.adaptive_interval = self.default_reminder_interval
        self.log_action(f'Adaptive interval set to {self.adaptive_interval}.')

    def check_user_focus(self):
        self.adjust_reminder_interval()
        if datetime.now() - self.last_interaction_time > self.adaptive_interval:
            self.emit_focus_reminder()
            self.last_interaction_time = datetime.now()  # Reset the timer after reminding

    def emit_focus_reminder(self):
        current_hour = datetime.now().hour
        if current_hour in self.user_patterns:
            self.user_patterns[current_hour]['reminders_issued'] += 1
            self.save_user_patterns()

        reminder_message = 'It seems you have been inactive for a while. Let\'s refocus on your tasks!'
        event_bus.emit('EMIT_SPEAK', {'message': reminder_message})
        self.log_action('Focus reminder emitted to user.')

    def start_monitoring(self):
        self.log_action('Adaptive focus monitoring started.')
        # Implement a mechanism to periodically call check_user_focus


def start_module(event_bus):
    focus_assistant = AdaptiveFocusAssistant()
    event_bus.subscribe('INTERACTION_EVENT', focus_assistant.handle_interaction_event)
    focus_assistant.start_monitoring()

    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
