import datetime
import time
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH
REMINDER_INTERVAL = 3600  # seconds (1 hour)

class MindfulnessReminder:
    def __init__(self):
        self.last_reminder_time = None

    def log(self, message):
        timestamp = datetime.datetime.now().isoformat()
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(f"{timestamp} - {message}\n")

    def handle_user_engagement(self, event_data):
        current_time = datetime.datetime.now()
        if self.last_reminder_time is None or (current_time - self.last_reminder_time).total_seconds() > REMINDER_INTERVAL:
            self.emit_mindfulness_reminder()
            self.last_reminder_time = current_time

    def emit_mindfulness_reminder(self):
        reminder_message = "It's time to take a short break and practice mindfulness!"
        event_bus.emit('EMIT_SPEAK', {
            'text': reminder_message,
            'token': str(time.time())
        })
        self.log(f"Mindfulness reminder emitted: {reminder_message}")


def start_module(event_bus):
    mindfulness_reminder = MindfulnessReminder()
    event_bus.subscribe('user_engagement_event', mindfulness_reminder.handle_user_engagement)
    print('Mindfulness Reminder module started and listening for user engagement events.')
