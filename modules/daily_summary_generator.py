import os
import json
import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/daily_summary.log'

class DailySummaryGenerator:
    def __init__(self):
        self.user_interactions = []
        self.emotion_trends = {}
        self.resource_usage = []
        self.anomalies_detected = []

    def log_interaction(self, event_data):
        """Log user interactions."""
        self.user_interactions.append(event_data)

    def log_emotion_trend(self, event_data):
        """Log emotion trends."""
        emotion = event_data.get('emotion_state')
        if emotion not in self.emotion_trends:
            self.emotion_trends[emotion] = 0
        self.emotion_trends[emotion] += 1

    def log_resource_usage(self, event_data):
        """Log system resource usage."""
        self.resource_usage.append(event_data)

    def log_anomaly(self, event_data):
        """Log any detected anomalies."""
        self.anomalies_detected.append(event_data)

    def generate_summary(self):
        """Generate and write the daily summary to the log file."""
        summary = {
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'user_interactions': len(self.user_interactions),
            'emotion_trends': self.emotion_trends,
            'resource_usage': self.resource_usage,
            'anomalies_detected': len(self.anomalies_detected)
        }
        self._write_log(summary)

    def _write_log(self, data):
        """Write the summary data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')
        print('Daily summary generated and logged.')

    def handle_end_of_day(self, event_data):
        """Handle end of day event to trigger summary generation."""
        self.generate_summary()


def start_module(event_bus):
    summary_generator = DailySummaryGenerator()
    event_bus.subscribe('USER_INTERACTION', summary_generator.log_interaction)
    event_bus.subscribe('EMIT_EMOTION_STATE', summary_generator.log_emotion_trend)
    event_bus.subscribe('RESOURCE_USAGE', summary_generator.log_resource_usage)
    event_bus.subscribe('ANOMALY_DETECTED', summary_generator.log_anomaly)
    event_bus.subscribe('END_OF_DAY', summary_generator.handle_end_of_day)
    
    print('Daily Summary Generator module started and listening for events.')
