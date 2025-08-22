import json
from core.event_bus import event_bus
from datetime import datetime

class AdaptiveCommunicationModule:
    def __init__(self):
        self.user_profiles = {}  # Store user communication preferences

    def handle_user_interaction(self, event_data):
        user_id = event_data.get('user_id')
        interaction = event_data.get('interaction')
        context = event_data.get('context')

        # Update user profile based on interaction and context
        self.update_user_profile(user_id, interaction, context)

        # Generate adaptive response
        response = self.generate_adaptive_response(user_id, context)

        # Emit the response
        event_bus.emit('adaptive_response', {'user_id': user_id, 'response': response})

    def update_user_profile(self, user_id, interaction, context):
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {'interactions': [], 'context_preferences': {}}

        # Update interaction history
        self.user_profiles[user_id]['interactions'].append((interaction, context))

        # Update context preferences
        if context not in self.user_profiles[user_id]['context_preferences']:
            self.user_profiles[user_id]['context_preferences'][context] = 0
        self.user_profiles[user_id]['context_preferences'][context] += 1

        self.log_action(f"Updated profile for user {user_id} with interaction '{interaction}' and context '{context}'.")

    def generate_adaptive_response(self, user_id, context):
        # Determine preferred context
        context_preferences = self.user_profiles[user_id]['context_preferences']
        preferred_context = max(context_preferences, key=context_preferences.get, default='neutral')

        # Generate response based on preferred context
        if preferred_context == 'formal':
            response = "Thank you for your interaction. How may I assist you further?"
        elif preferred_context == 'informal':
            response = "Hey! What can I do for you today?"
        else:
            response = "How can I help you?"

        self.log_action(f"Generated adaptive response for user {user_id}: '{response}'")
        return response

    def log_action(self, message):
        log_path = '/home/triad/mitch/logs/adaptive_communication.log'
        with open(log_path, 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")


def start_module(event_bus):
    communication_module = AdaptiveCommunicationModule()
    event_bus.subscribe('user_interaction', communication_module.handle_user_interaction)
    communication_module.log_action("Adaptive Communication Module started.")
