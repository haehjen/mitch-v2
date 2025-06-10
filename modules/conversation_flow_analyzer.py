import os
import json
import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/conversation_flow_analyzer.log'

class ConversationFlowAnalyzer:
    def __init__(self):
        self.interactions = []

    def log_interaction(self, event_data):
        """Log interaction details from event_data."""
        timestamp = datetime.datetime.now().isoformat()
        interaction_data = {
            'timestamp': timestamp,
            'interaction': event_data.get('interaction'),
            'duration': event_data.get('duration'),
            'interruption': event_data.get('interruption', False)
        }
        self.interactions.append(interaction_data)
        self._write_log(interaction_data)

    def _write_log(self, data):
        """Write the interaction data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def analyze_conversation_flow(self):
        """Analyze the logged interactions to detect patterns and propose improvements."""
        summary = {'total_interactions': len(self.interactions), 'interruptions': 0, 'average_duration': 0}
        total_duration = 0

        for entry in self.interactions:
            total_duration += entry['duration']
            if entry['interruption']:
                summary['interruptions'] += 1

        if len(self.interactions) > 0:
            summary['average_duration'] = total_duration / len(self.interactions)

        return summary

    def handle_interaction_event(self, event_data):
        """Handle interaction events emitted by other modules."""
        self.log_interaction(event_data)
        summary = self.analyze_conversation_flow()
        self._write_log({'summary': summary})


def start_module(event_bus):
    conversation_analyzer = ConversationFlowAnalyzer()
    event_bus.subscribe('EMIT_INTERACTION', conversation_analyzer.handle_interaction_event)
    
    print('Conversation Flow Analyzer module started and listening for interaction events.')
