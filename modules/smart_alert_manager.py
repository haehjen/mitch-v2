import os
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/smart_alert_manager.log'

class SmartAlertManager:
    def __init__(self):
        self.alert_queue = []
        self.priorities = {
            'high': 3,
            'medium': 2,
            'low': 1
        }

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_alert(self, alert_data):
        priority = alert_data.get('priority', 'low')
        self.alert_queue.append((priority, alert_data))
        self.log_action(f'Alert received: {alert_data}')
        self.process_alerts()

    def process_alerts(self):
        if not self.alert_queue:
            return

        # Sort alerts by priority
        self.alert_queue.sort(key=lambda x: self.priorities[x[0]], reverse=True)
        highest_priority_alert = self.alert_queue.pop(0)
        self.emit_alert(highest_priority_alert[1])

    def emit_alert(self, alert_data):
        message = alert_data.get('message', 'No message provided')
        event_bus.emit('EMIT_SPEAK', {'message': message})
        self.log_action(f'Alert emitted: {alert_data}')


def start_module(event_bus):
    alert_manager = SmartAlertManager()
    event_bus.subscribe('ALERT', alert_manager.handle_alert)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
