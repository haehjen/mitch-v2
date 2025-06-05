import os
import json
datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/emotion_tracker.log'

class EmotionTracker:
    def __init__(self):
        self.emotion_states = []

    def log_emotion_state(self, event_data):
        """Log the emotional state from event_data."""
        timestamp = datetime.datetime.now().isoformat()
        emotion_data = {
            'timestamp': timestamp,
            'emotion_state': event_data.get('emotion_state')
        }
        self.emotion_states.append(emotion_data)
        self._write_log(emotion_data)

    def _write_log(self, data):
        """Write the emotion data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def summarize_emotions(self):
        """Summarize the logged emotions."""
        summary = {}
        for entry in self.emotion_states:
            emotion = entry['emotion_state']
            if emotion not in summary:
                summary[emotion] = 0
            summary[emotion] += 1
        return summary

    def handle_emotion_event(self, event_data):
        """Handle emotion events emitted by other modules."""
        self.log_emotion_state(event_data)


def start_module(event_bus):
    emotion_tracker = EmotionTracker()
    event_bus.subscribe('EMIT_EMOTION_STATE', emotion_tracker.handle_emotion_event)
    
    print('Emotion Tracker module started and listening for emotion state events.')
