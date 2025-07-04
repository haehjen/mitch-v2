import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_communication_assistant.log'

class AdaptiveCommunicationAssistant:
    def __init__(self):
        self.user_preferences = self.load_user_preferences()
        self.default_tone = 'neutral'
        self.default_verbosity = 'medium'

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_user_preferences(self):
        try:
            with open('/home/triad/mitch/data/user_preferences.json', 'r') as file:
                preferences = json.load(file)
                self.log_action('User preferences loaded successfully.')
                return preferences
        except FileNotFoundError:
            self.log_action('No user preferences file found, using defaults.')
            return {}

    def update_communication_style(self, context):
        tone = self.user_preferences.get('tone', self.default_tone)
        verbosity = self.user_preferences.get('verbosity', self.default_verbosity)
        self.log_action(f'Updating communication style to tone: {tone}, verbosity: {verbosity}.')
        # More complex logic can be added here to adjust communication based on the context

    def handle_user_feedback(self, feedback_data):
        # Process feedback and adjust preferences
        feedback_tone = feedback_data.get('tone')
        feedback_verbosity = feedback_data.get('verbosity')
        if feedback_tone:
            self.user_preferences['tone'] = feedback_tone
            self.log_action(f'User feedback received. Tone updated to: {feedback_tone}.')
        if feedback_verbosity:
            self.user_preferences['verbosity'] = feedback_verbosity
            self.log_action(f'User feedback received. Verbosity updated to: {feedback_verbosity}.')
        self.save_user_preferences()

    def save_user_preferences(self):
        with open('/home/triad/mitch/data/user_preferences.json', 'w') as file:
            json.dump(self.user_preferences, file)
            self.log_action('User preferences saved successfully.')

    def start_monitoring_feedback(self):
        self.log_action('Adaptive communication monitoring started.')


def start_module(event_bus):
    comm_assistant = AdaptiveCommunicationAssistant()
    event_bus.subscribe('USER_FEEDBACK', comm_assistant.handle_user_feedback)
    comm_assistant.start_monitoring_feedback()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
