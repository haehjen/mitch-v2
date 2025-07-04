import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_learning_assistant.log'
DATA_FILE = '/home/triad/mitch/data/learning_progress.json'

class AdaptiveLearningAssistant:
    def __init__(self):
        self.learning_data = self.load_learning_data()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_learning_data(self):
        try:
            with open(DATA_FILE, 'r') as file:
                data = json.load(file)
                self.log_action('Learning data loaded successfully.')
                return data
        except FileNotFoundError:
            self.log_action('No existing learning data file found, starting fresh.')
            return {}

    def save_learning_data(self):
        with open(DATA_FILE, 'w') as file:
            json.dump(self.learning_data, file)
            self.log_action('Learning data saved successfully.')

    def update_learning_progress(self, event_data):
        user_id = event_data.get('user_id')
        topic = event_data.get('topic')
        progress = event_data.get('progress')
        if user_id not in self.learning_data:
            self.learning_data[user_id] = {}
        self.learning_data[user_id][topic] = progress
        self.save_learning_data()
        self.log_action(f'Progress updated for user {user_id} on topic {topic}: {progress}')

    def recommend_next_steps(self, event_data):
        user_id = event_data.get('user_id')
        current_topic = event_data.get('current_topic')
        user_progress = self.learning_data.get(user_id, {})
        next_topic = self.determine_next_topic(user_progress, current_topic)
        recommendation_message = f'User {user_id}, based on your progress, consider focusing on {next_topic} next.'
        event_bus.emit('EMIT_SPEAK', {'message': recommendation_message})
        self.log_action(f'Recommendation made for user {user_id}: {next_topic}')

    def determine_next_topic(self, user_progress, current_topic):
        # Placeholder logic for determining the next topic
        topics = ['Math', 'Science', 'History', 'Art']
        if current_topic in topics:
            current_index = topics.index(current_topic)
            next_index = (current_index + 1) % len(topics)
            return topics[next_index]
        return topics[0]

    def start_monitoring(self):
        self.log_action('Adaptive learning monitoring started.')


def start_module(event_bus):
    learning_assistant = AdaptiveLearningAssistant()
    event_bus.subscribe('UPDATE_LEARNING_PROGRESS', learning_assistant.update_learning_progress)
    event_bus.subscribe('REQUEST_RECOMMENDATION', learning_assistant.recommend_next_steps)
    learning_assistant.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
