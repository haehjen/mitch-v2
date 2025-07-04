import os
from datetime import datetime, timedelta
from threading import Thread, Event
from time import sleep
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_break_reminder.log'

class AdaptiveBreakReminder:
    def __init__(self):
        self.last_break_time = datetime.now()
        self.break_interval = timedelta(minutes=60)  # Default break interval
        self.stop_event = Event()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_interaction_event(self, event_data):
        # Update the last break time if user interaction is detected
        self.last_break_time = datetime.now()
        self.log_action('User interaction detected, resetting break timer.')

    def check_for_break(self):
        # Check if it's time to remind the user to take a break
        if datetime.now() - self.last_break_time > self.break_interval:
            self.emit_break_reminder()
            self.last_break_time = datetime.now()  # Reset break timer

    def emit_break_reminder(self):
        reminder_message = "You've been working for a while. It's time to take a short break!"
        event_bus.emit('EMIT_SPEAK', {'message': reminder_message})
        self.log_action('Break reminder emitted to user.')

    def start_monitoring(self):
        self.log_action('Adaptive break monitoring started.')
        while not self.stop_event.is_set():
            self.check_for_break()
            sleep(60)  # Check every minute

    def stop(self):
        self.stop_event.set()
        self.log_action('Adaptive break monitoring stopped.')


def start_module(event_bus):
    break_reminder = AdaptiveBreakReminder()
    Thread(target=break_reminder.start_monitoring, daemon=True).start()
    event_bus.subscribe('INTERACTION_EVENT', break_reminder.handle_interaction_event)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
