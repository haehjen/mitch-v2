import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/contextual_focus_booster.log'

class ContextualFocusBooster:
    def __init__(self):
        self.context = {}

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_context_update(self, event_data):
        # Update the current context with new data
        self.context.update(event_data)
        self.log_action(f'Context updated: {event_data}')

    def offer_focus_boost(self):
        # Analyze the current context and suggest focus boosting strategies
        if 'distraction_level' in self.context and self.context['distraction_level'] > 5:
            suggestion = "Consider taking a short break to refresh your mind."
        elif 'task_importance' in self.context and self.context['task_importance'] > 7:
            suggestion = "Focus on deep work and minimize distractions."
        else:
            suggestion = "Maintain your current pace for optimal productivity."
        event_bus.emit('EMIT_SPEAK', {'message': suggestion})
        self.log_action(f'Focus boost suggestion emitted: {suggestion}')

    def start_monitoring(self):
        self.log_action('Contextual focus monitoring started.')
        # You could implement a mechanism to periodically call offer_focus_boost
        # using a scheduler or another mechanism within MITCH.


def start_module(event_bus):
    focus_booster = ContextualFocusBooster()
    event_bus.subscribe('CONTEXT_UPDATE', focus_booster.handle_context_update)
    focus_booster.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
