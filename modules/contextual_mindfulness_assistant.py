import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/contextual_mindfulness_assistant.log'

class ContextualMindfulnessAssistant:
    def __init__(self):
        self.mindfulness_interval = timedelta(minutes=60)  # Suggest mindfulness every 60 minutes
        self.last_mindfulness_time = datetime.now()
        self.user_mood = 'neutral'

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_mood_event(self, event_data):
        # Update the user's mood based on the latest event
        self.user_mood = event_data.get('mood', 'neutral')
        self.log_action(f'Received mood event: {self.user_mood}')

    def check_for_mindfulness_prompt(self):
        # Determine if it's time to prompt for mindfulness
        if datetime.now() - self.last_mindfulness_time > self.mindfulness_interval:
            if self.user_mood in ['stressed', 'anxious', 'neutral']:
                self.emit_mindfulness_prompt()
                self.last_mindfulness_time = datetime.now()

    def emit_mindfulness_prompt(self):
        # Emit a mindfulness prompt to the user
        prompt_message = 'Take a moment to focus on your breath and clear your mind. A short mindfulness exercise can help improve your focus and reduce stress.'
        event_bus.emit('EMIT_SPEAK', {'message': prompt_message})
        self.log_action('Mindfulness prompt emitted to user.')

    def start_monitoring(self):
        self.log_action('Contextual mindfulness monitoring started.')
        # Set up a mechanism to periodically check for mindfulness prompts
        # This could be implemented using a scheduler or another mechanism within MITCH.


def start_module(event_bus):
    mindfulness_assistant = ContextualMindfulnessAssistant()
    event_bus.subscribe('MOOD_EVENT', mindfulness_assistant.handle_mood_event)
    mindfulness_assistant.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
