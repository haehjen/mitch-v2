import re
from core.event_bus import event_bus

class EmotionBasedResponse:
    def __init__(self):
        self.emotion_keywords = {
            'happy': ['glad', 'happy', 'joyful', 'excited', 'pleased'],
            'sad': ['sad', 'unhappy', 'sorrow', 'depressed', 'down'],
            'angry': ['angry', 'mad', 'furious', 'irritated', 'annoyed'],
            'neutral': []  # Fallback for neutrality
        }
        self.user_emotion = 'neutral'

    def detect_emotion(self, message):
        """Detects emotion based on keywords in the message."""
        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', message, re.IGNORECASE):
                    return emotion
        return 'neutral'

    def adjust_response(self, emotion):
        """Adjusts MITCH's response based on the detected emotion."""
        response_tone = {
            'happy': "I'm glad to hear that! How can I assist you further?",
            'sad': "I'm here to help. Let me know if there's anything I can do.",
            'angry': "I understand things can be frustrating. How can I assist you?",
            'neutral': "How can I assist you today?"
        }
        return response_tone.get(emotion, "How can I assist you today?")

    def handle_interaction_event(self, event_data):
        """Handles user interaction events to detect emotion and adjust response."""
        user_message = event_data.get('message', '')
        self.user_emotion = self.detect_emotion(user_message)
        adjusted_response = self.adjust_response(self.user_emotion)
        event_bus.emit('EMIT_SPEAK', {'response': adjusted_response})
        self.log_emotion_detection(user_message, self.user_emotion)

    def log_emotion_detection(self, message, emotion):
        """Logs the detected emotion and the corresponding message."""
        log_entry = f"Detected emotion: {emotion} from message: {message}\n"
        with open('/home/triad/mitch/logs/emotion_based_response.log', 'a') as log_file:
            log_file.write(log_entry)


def start_module(event_bus):
    emotion_response_module = EmotionBasedResponse()
    event_bus.subscribe('INTERACTION_SUMMARY', emotion_response_module.handle_interaction_event)
