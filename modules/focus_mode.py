import os
import json
import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/focus_mode.log'

class FocusMode:
    def __init__(self):
        self.active = False

    def toggle_focus_mode(self, event_data):
        """Toggle focus mode on or off based on event data."""
        self.active = not self.active
        action = 'activated' if self.active else 'deactivated'
        self.log_focus_mode_change(action)

        if self.active:
            self.suppress_non_essential_events()
            event_bus.emit('FOCUS_MODE_ACTIVATED', {'timestamp': datetime.datetime.now().isoformat()})
        else:
            self.restore_normal_operations()
            event_bus.emit('FOCUS_MODE_DEACTIVATED', {'timestamp': datetime.datetime.now().isoformat()})

    def suppress_non_essential_events(self):
        """Suppress non-essential events to minimize distractions."""
        # Example: stop emitting notifications or non-urgent alerts
        # This would involve interacting with other modules to ensure their events are suppressed
        print("Non-essential events suppressed.")

    def restore_normal_operations(self):
        """Restore normal operations after focus mode is deactivated."""
        # Example: resume normal event emissions
        print("Normal operations restored.")

    def log_focus_mode_change(self, action):
        """Log the change in focus mode state."""
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'action': action
        }
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')


def start_module(event_bus):
    focus_mode = FocusMode()
    event_bus.subscribe('TOGGLE_FOCUS_MODE', focus_mode.toggle_focus_mode)
    
    print('Focus Mode module started and listening for toggle events.')
