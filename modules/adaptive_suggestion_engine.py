import os
import json
from datetime import datetime
from core.event_bus import event_bus

class AdaptiveSuggestionEngine:
    def __init__(self):
        self.suggestions_log = '/home/triad/mitch/logs/adaptive_suggestions.log'
        self.load_suggestions()

    def load_suggestions(self):
        if os.path.exists(self.suggestions_log):
            with open(self.suggestions_log, 'r') as file:
                self.suggestions = json.load(file)
        else:
            self.suggestions = []

    def log_suggestion(self, suggestion):
        self.suggestions.append(suggestion)
        with open(self.suggestions_log, 'w') as file:
            json.dump(self.suggestions, file)

    def analyze_user_behavior(self, event_data):
        # Placeholder for behavior analysis logic
        # Example: if user is inactive for a long period, suggest a break reminder
        suggestion = {
            'timestamp': datetime.now().isoformat(),
            'type': 'behavior',
            'message': 'Consider taking a break to improve productivity'
        }
        self.log_suggestion(suggestion)
        self.emit_suggestion(suggestion)

    def analyze_system_performance(self, event_data):
        # Placeholder for system performance analysis logic
        # Example: if high CPU usage is detected, suggest closing unused applications
        suggestion = {
            'timestamp': datetime.now().isoformat(),
            'type': 'performance',
            'message': 'High CPU usage detected. Consider closing unused applications.'
        }
        self.log_suggestion(suggestion)
        self.emit_suggestion(suggestion)

    def emit_suggestion(self, suggestion):
        event_bus.emit('suggestion_generated', suggestion)


def start_module(event_bus):
    engine = AdaptiveSuggestionEngine()
    event_bus.subscribe('user_behavior_analyzed', engine.analyze_user_behavior)
    event_bus.subscribe('system_performance_analyzed', engine.analyze_system_performance)
    
    # Log the module start
    with open('/home/triad/mitch/logs/module_start.log', 'a') as log_file:
        log_file.write(f"{datetime.now()} - Adaptive Suggestion Engine module started.\n")
