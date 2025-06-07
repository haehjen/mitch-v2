import os
import json
import datetime
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

logger = get_logger("emotion_tracker")

class EmotionTracker:
    def __init__(self):
        self.emotion_states = []

    def log_emotion_state(self, event_data):
        """Log the emotional state from event_data."""
        timestamp = datetime.datetime.now().isoformat()
        emotion_state = event_data.get('emotion_state')
        emotion_data = {
            'timestamp': timestamp,
            'emotion_state': emotion_state
        }
        self.emotion_states.append(emotion_data)

        logger.info(json.dumps(emotion_data))  # Store full emotion entry

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
    
    logger.info("Emotion Tracker module started and listening for emotion state events.")
