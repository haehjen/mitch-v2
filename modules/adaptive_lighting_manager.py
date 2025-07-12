import os
from datetime import datetime, time
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_lighting_manager.log'

class AdaptiveLightingManager:
    def __init__(self):
        self.current_lighting = 'normal'

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def adjust_lighting(self, new_lighting):
        # Placeholder for actual lighting control logic
        self.current_lighting = new_lighting
        self.log_action(f'Lighting adjusted to: {new_lighting}')

    def determine_lighting(self):
        current_time = datetime.now().time()
        if time(6, 0) <= current_time < time(18, 0):
            return 'daylight'
        else:
            return 'evening'

    def handle_time_update(self, event_data):
        new_lighting = self.determine_lighting()
        if new_lighting != self.current_lighting:
            self.adjust_lighting(new_lighting)

    def handle_user_interaction(self, event_data):
        if event_data.get('action') == 'focus':
            self.adjust_lighting('focus')
        elif event_data.get('action') == 'relax':
            self.adjust_lighting('relax')


def start_module(event_bus):
    lighting_manager = AdaptiveLightingManager()
    event_bus.subscribe('TIME_UPDATE', lighting_manager.handle_time_update)
    event_bus.subscribe('USER_INTERACTION', lighting_manager.handle_user_interaction)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
