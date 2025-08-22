import os
from datetime import datetime
from core.event_bus import event_bus

class ProactivityEnhancer:
    def __init__(self):
        self.suggestions_log = '/home/triad/mitch/logs/proactivity_enhancer.log'

    def analyze_user_engagement(self, data):
        # Analyze user engagement and suggest improvements
        if data['total_interactions'] == 0:
            self.log_suggestion("User has not interacted recently. Consider prompting engagement activities.")

    def analyze_memory_usage(self, data):
        # Analyze memory usage and suggest optimizations
        if data.get('memory_usage', 0) > 80:
            self.log_suggestion("High memory usage detected. Recommend reviewing running processes.")

    def analyze_system_logs(self, data):
        # Analyze system logs for potential issues
        log_summary = data.get('summary', '')
        if 'error' in log_summary.lower():
            self.log_suggestion("Errors found in recent logs. Recommend diagnostics to identify issues.")

    def log_suggestion(self, suggestion):
        with open(self.suggestions_log, 'a') as log_file:
            log_file.write(f"{datetime.now()} - Suggestion: {suggestion}\n")

    def handle_user_engagement_event(self, event_data):
        self.analyze_user_engagement(event_data)

    def handle_system_logs_event(self, event_data):
        self.analyze_system_logs(event_data)

    def handle_memory_event(self, event_data):
        self.analyze_memory_usage(event_data)


def start_module(event_bus):
    enhancer = ProactivityEnhancer()
    
    event_bus.subscribe('user_engagement_update', enhancer.handle_user_engagement_event)
    event_bus.subscribe('system_logs_update', enhancer.handle_system_logs_event)
    event_bus.subscribe('memory_usage_update', enhancer.handle_memory_event)

    enhancer.log_suggestion("Proactivity Enhancer module started.")
