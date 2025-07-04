import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/user_proximity_notifier.log'

class UserProximityNotifier:
    def __init__(self):
        self.proximity_threshold = 5  # Example threshold in meters

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_proximity_event(self, event_data):
        # Process the event to determine if proximity threshold is met
        distance = event_data.get('distance', None)
        if distance is not None:
            self.log_action(f'Proximity event received with distance: {distance}m')
            if distance < self.proximity_threshold:
                self.emit_proximity_alert(distance)

    def emit_proximity_alert(self, distance):
        alert_message = f'User detected within {distance} meters. Adjusting system settings for optimal interaction.'
        event_bus.emit('EMIT_SPEAK', {'message': alert_message})
        self.log_action('Proximity alert emitted to user.')

    def start_monitoring(self):
        self.log_action('User proximity monitoring started.')


def start_module(event_bus):
    proximity_notifier = UserProximityNotifier()
    event_bus.subscribe('PROXIMITY_EVENT', proximity_notifier.handle_proximity_event)
    proximity_notifier.start_monitoring()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
