import os
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/mood_based_recommendation.log'

class MoodBasedRecommendation:
    def __init__(self):
        self.recommendations = {
            'happy': ['Listen to upbeat music', 'Watch a comedy', 'Go for a walk'],
            'sad': ['Call a friend', 'Watch a feel-good movie', 'Write in a journal'],
            'angry': ['Try meditation', 'Do a workout', 'Practice deep breathing'],
            'neutral': ['Read a book', 'Learn something new', 'Organize your space']
        }

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_emotion_event(self, event_data):
        emotion = event_data.get('emotion')
        if emotion in self.recommendations:
            suggestion = self.get_recommendation(emotion)
            self.emit_recommendation(suggestion)
            self.log_action(f'Recommendation for {emotion} mood: {suggestion}')

    def get_recommendation(self, emotion):
        import random
        return random.choice(self.recommendations[emotion])

    def emit_recommendation(self, recommendation):
        event_bus.emit('EMIT_SPEAK', {'message': f'Suggestion: {recommendation}'})


def start_module(event_bus):
    mood_recommender = MoodBasedRecommendation()
    event_bus.subscribe('EMOTION_EVENT', mood_recommender.handle_emotion_event)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
