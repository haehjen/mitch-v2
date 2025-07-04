import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/dynamic_contextual_responder.log'

class DynamicContextualResponder:
    def __init__(self):
        self.context_data = {}
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
            self.context_data = {}
            self.log_action('No existing context data file found, starting fresh.')

    def save_context_data(self):
        with open('/home/triad/mitch/data/context_data.json', 'w') as file:
            json.dump(self.context_data, file)
            self.log_action('Context data saved successfully.')

    def handle_interaction_event(self, event_data):
        # Update context data based on user interactions
        user_id = event_data.get('user_id', 'unknown_user')
        interaction_time = datetime.now().isoformat()
        self.context_data[user_id] = {'last_interaction': interaction_time}
        self.save_context_data()
        self.log_action(f'Interaction event processed for user: {user_id}')

    def generate_contextual_response(self, event_data):
        # Create a contextual response based on current data
        user_id = event_data.get('user_id', 'unknown_user')
        last_interaction = self.context_data.get(user_id, {}).get('last_interaction', 'unknown')
        response_message = f'Hello {user_id}, your last interaction was at {last_interaction}. How can I assist you now?'
        event_bus.emit('EMIT_SPEAK', {'message': response_message})
        self.log_action(f'Contextual response generated for user: {user_id}')

    def start_monitoring(self):
        self.log_action('Dynamic contextual responder monitoring started.')


def start_module(event_bus):
    responder = DynamicContextualResponder()
    event_bus.subscribe('INTERACTION_EVENT', responder.handle_interaction_event)
    event_bus.subscribe('REQUEST_CONTEXTUAL_RESPONSE', responder.generate_contextual_response)
    responder.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
