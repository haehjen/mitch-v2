import os
import datetime
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class AdaptiveEnergySaver:
    def __init__(self):
        self.last_active_time = datetime.datetime.now()
        self.inactive_threshold = datetime.timedelta(minutes=10)  # Threshold for inactivity

    def log_action(self, action):
        """Log the power-saving action taken."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(f'{datetime.datetime.now().isoformat()} - {action}\n')

    def handle_system_activity(self, event_data):
        """Update the last active time based on system activity."""
        self.last_active_time = datetime.datetime.now()
        self.log_action('System activity detected, resetting inactivity timer.')

    def check_inactivity(self):
        """Check if the system has been inactive for longer than the threshold."""
        current_time = datetime.datetime.now()
        if current_time - self.last_active_time > self.inactive_threshold:
            self.activate_power_saving_mode()

    def activate_power_saving_mode(self):
        """Trigger actions to reduce energy consumption."""
        # Placeholder for actual power-saving actions, e.g., reduce CPU speed, dim screen
        self.log_action('Activating power-saving mode due to inactivity.')
        # Emit an event or call a system command to reduce power usage
        # Example: os.system('xset dpms force off')

    def start_monitoring(self):
        """Continuously monitor for inactivity and trigger power-saving mode when needed."""
        while True:
            self.check_inactivity()
            time.sleep(60)  # Check every minute


def start_module(event_bus):
    energy_saver = AdaptiveEnergySaver()
    event_bus.subscribe('SYSTEM_ACTIVITY', energy_saver.handle_system_activity)
    
    # Start monitoring in a separate thread to avoid blocking
    import threading
    monitor_thread = threading.Thread(target=energy_saver.start_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()

    print('Adaptive Energy Saver module started and monitoring for inactivity.')
