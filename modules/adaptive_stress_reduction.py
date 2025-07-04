import os
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_stress_reduction.log'

class AdaptiveStressReduction:
    def __init__(self):
        self.break_recommendation_interval = timedelta(minutes=60)  # Recommend breaks every 60 minutes
        self.last_break_recommendation_time = datetime.now()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def monitor_user_activity(self, event_data):
        # Update the last interaction time whenever an interaction occurs
        current_time = datetime.now()
        if current_time - self.last_break_recommendation_time > self.break_recommendation_interval:
            self.emit_break_recommendation()
            self.last_break_recommendation_time = current_time  # Reset the timer after recommending a break

    def emit_break_recommendation(self):
        recommendation_message = "You've been working hard. Consider taking a short break to recharge!"
        event_bus.emit('EMIT_SPEAK', {'message': recommendation_message})
        self.log_action('Break recommendation emitted to user.')

    def start_monitoring(self):
        self.log_action('Adaptive stress reduction monitoring started.')
        # You could implement a mechanism to periodically call monitor_user_activity


def start_module(event_bus):
    stress_reduction = AdaptiveStressReduction()
    event_bus.subscribe('INTERACTION_EVENT', stress_reduction.monitor_user_activity)
    stress_reduction.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
