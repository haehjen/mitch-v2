import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/contextual_insights.log'

class ContextualInsights:
    def __init__(self):
        self.context_data = []
        self.load_context_data()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_context_data(self):
        try:
            with open('/home/triad/mitch/data/context_data.json', 'r') as file:
                self.context_data = json.load(file)
                self.log_action('Context data loaded successfully.')
        except FileNotFoundError:
            self.context_data = []
            self.log_action('No existing context data file found, starting fresh.')

    def save_context_data(self):
        with open('/home/triad/mitch/data/context_data.json', 'w') as file:
            json.dump(self.context_data, file)
            self.log_action('Context data saved successfully.')

    def handle_interaction_event(self, event_data):
        # Extract relevant information from event data and update context
        interaction_info = {
            'time': datetime.now().isoformat(),
            'event': event_data.get('event_type'),
            'details': event_data.get('details', {})
        }
        self.context_data.append(interaction_info)
        self.save_context_data()
        self.log_action(f'Interaction event recorded: {interaction_info}')

    def analyze_context(self):
        # Analyze the context data for patterns or insights
        if len(self.context_data) > 5:  # Example threshold
            suggestion = 'Consider taking a break, as multiple interactions were detected in a short span.'
            event_bus.emit('EMIT_SPEAK', {'message': suggestion})
            self.log_action('Contextual insight emitted to user.')

    def start_monitoring(self):
        self.log_action('Contextual insights monitoring started.')
        # You could implement a mechanism to periodically call analyze_context
        # using a scheduler or another mechanism within MITCH.


def start_module(event_bus):
    insights = ContextualInsights()
    event_bus.subscribe('INTERACTION_EVENT', insights.handle_interaction_event)
    insights.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
