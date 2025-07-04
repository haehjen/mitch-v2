import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/contextual_reminder.log'

class ContextualReminder:
    def __init__(self):
        self.contextual_data = {}
        self.load_contextual_data()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_contextual_data(self):
        try:
            with open('/home/triad/mitch/data/contextual_data.json', 'r') as file:
                self.contextual_data = json.load(file)
                self.log_action('Contextual data loaded successfully.')
        except FileNotFoundError:
            self.contextual_data = {}
            self.log_action('No existing contextual data file found, starting fresh.')

    def save_contextual_data(self):
        with open('/home/triad/mitch/data/contextual_data.json', 'w') as file:
            json.dump(self.contextual_data, file)
            self.log_action('Contextual data saved successfully.')

    def handle_interaction_event(self, event_data):
        # Update contextual data based on user interactions
        self.contextual_data.update(event_data)
        self.save_contextual_data()
        self.log_action('Contextual data updated with new interaction event.')

    def provide_contextual_reminder(self):
        # Analyze contextual data to provide relevant reminders
        if 'task' in self.contextual_data:
            reminder_message = f"Don't forget to complete your task: {self.contextual_data['task']}"
            event_bus.emit('EMIT_SPEAK', {'message': reminder_message})
            self.log_action(f'Contextual reminder emitted: {reminder_message}')

    def start_monitoring(self):
        self.log_action('Contextual reminder monitoring started.')
        # This could be integrated with a scheduler to periodically call provide_contextual_reminder()


def start_module(event_bus):
    contextual_reminder = ContextualReminder()
    event_bus.subscribe('INTERACTION_EVENT', contextual_reminder.handle_interaction_event)
    contextual_reminder.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
