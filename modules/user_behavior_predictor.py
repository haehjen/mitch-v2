import json
import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/user_behavior_predictor.log'

class UserBehaviorPredictor:
    def __init__(self):
        self.behavior_patterns = []

    def log_behavior(self, event_data):
        """Log user behavior from event_data."""
        timestamp = datetime.datetime.now().isoformat()
        behavior_data = {
            'timestamp': timestamp,
            'behavior': event_data.get('behavior')
        }
        self.behavior_patterns.append(behavior_data)
        self._write_log(behavior_data)

    def _write_log(self, data):
        """Write the behavior data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def predict_behavior(self):
        """Predict future behaviors based on logged patterns."""
        # Analyzing logged patterns to predict future actions
        predictions = {}
        for entry in self.behavior_patterns:
            behavior = entry['behavior']
            if behavior not in predictions:
                predictions[behavior] = 0
            predictions[behavior] += 1
        # Determine most likely future behavior
        if predictions:
            predicted_behavior = max(predictions, key=predictions.get)
            return predicted_behavior
        return None

    def handle_behavior_event(self, event_data):
        """Handle behavior events emitted by other modules."""
        self.log_behavior(event_data)
        predicted_behavior = self.predict_behavior()
        if predicted_behavior:
            event_bus.emit('PREDICTED_BEHAVIOR', {'predicted_behavior': predicted_behavior})


def start_module(event_bus):
    user_behavior_predictor = UserBehaviorPredictor()
    event_bus.subscribe('EMIT_USER_BEHAVIOR', user_behavior_predictor.handle_behavior_event)
    print('User Behavior Predictor module started and listening for user behavior events.')
