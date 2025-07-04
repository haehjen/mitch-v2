import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/user_feedback_collector.log'
FEEDBACK_FILE = '/home/triad/mitch/data/user_feedback.json'

class UserFeedbackCollector:
    def __init__(self):
        self.feedback_data = []
        self.load_feedback()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_feedback(self):
        try:
            with open(FEEDBACK_FILE, 'r') as file:
                self.feedback_data = json.load(file)
                self.log_action('Feedback data loaded successfully.')
        except FileNotFoundError:
            self.feedback_data = []
            self.log_action('No existing feedback file found, starting fresh.')

    def save_feedback(self):
        with open(FEEDBACK_FILE, 'w') as file:
            json.dump(self.feedback_data, file)
            self.log_action('Feedback data saved successfully.')

    def handle_feedback_event(self, event_data):
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'feedback': event_data.get('feedback', ''),
            'user': event_data.get('user', 'unknown')
        }
        self.feedback_data.append(feedback_entry)
        self.save_feedback()
        self.log_action(f'Feedback recorded: {feedback_entry}')

    def start_monitoring(self):
        self.log_action('User feedback monitoring started.')


def start_module(event_bus):
    feedback_collector = UserFeedbackCollector()
    event_bus.subscribe('USER_FEEDBACK', feedback_collector.handle_feedback_event)
    feedback_collector.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
