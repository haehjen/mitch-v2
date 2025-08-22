import json
import os
from core.event_bus import event_bus
from datetime import datetime

class AdaptiveLearning:
    def __init__(self):
        self.user_data_file = '/home/triad/mitch/data/user_interactions.json'
        self.interactions = self.load_interactions()

    def load_interactions(self):
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r') as file:
                return json.load(file)
        return {}

    def save_interactions(self):
        with open(self.user_data_file, 'w') as file:
            json.dump(self.interactions, file)

    def log_interaction(self, user_intent, response):
        timestamp = datetime.now().isoformat()
        if user_intent not in self.interactions:
            self.interactions[user_intent] = []
        self.interactions[user_intent].append({'timestamp': timestamp, 'response': response})
        self.save_interactions()

    def analyze_feedback(self, feedback):
        # Here, simple placeholder logic is used to simulate feedback analysis.
        # In a more complex system, natural language processing could be applied.
        sentiment = 'positive' if 'good' in feedback.lower() else 'negative'
        return sentiment

    def handle_user_feedback(self, event_data):
        user_intent = event_data.get('user_intent')
        feedback = event_data.get('feedback')
        sentiment = self.analyze_feedback(feedback)
        self.log_action(f"Feedback received for intent '{user_intent}': {feedback} (Sentiment: {sentiment})")

    def log_action(self, message):
        log_path = '/home/triad/mitch/logs/adaptive_learning.log'
        with open(log_path, 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")

adaptive_learning = AdaptiveLearning()

def start_module(event_bus):
    """
    Entry point for the Adaptive Learning module.
    """
    def handle_user_interaction(event_data):
        user_intent = event_data.get('user_intent')
        response = event_data.get('response')
        adaptive_learning.log_interaction(user_intent, response)
        adaptive_learning.log_action(f"Logged interaction for intent '{user_intent}' with response: {response}")

    event_bus.subscribe('user_interaction', handle_user_interaction)
    event_bus.subscribe('user_feedback', adaptive_learning.handle_user_feedback)
