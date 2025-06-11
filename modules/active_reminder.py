import datetime
import json
import time
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/active_reminder.log'

class ActiveReminder:
    def __init__(self):
        self.reminders = []
        self.load_reminders()

    def load_reminders(self):
        try:
            with open(LOG_FILE_PATH, 'r') as log_file:
                self.reminders = json.load(log_file)
        except FileNotFoundError:
            self.reminders = []
        except json.JSONDecodeError:
            self.reminders = []

    def save_reminders(self):
        with open(LOG_FILE_PATH, 'w') as log_file:
            json.dump(self.reminders, log_file)

    def add_reminder(self, event_data):
        reminder_time = event_data.get('reminder_time')
        task_description = event_data.get('task_description')
        if reminder_time and task_description:
            self.reminders.append({'reminder_time': reminder_time, 'task_description': task_description})
            self.save_reminders()
            event_bus.emit('EMIT_SPEAK', f"Reminder set for {task_description} at {reminder_time}.")

    def check_reminders(self):
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        reminders_to_remove = []
        for reminder in self.reminders:
            if reminder['reminder_time'] <= current_time:
                event_bus.emit('EMIT_SPEAK', f"Reminder: {reminder['task_description']}.")
                reminders_to_remove.append(reminder)
        self.reminders = [reminder for reminder in self.reminders if reminder not in reminders_to_remove]
        if reminders_to_remove:
            self.save_reminders()

    def handle_task_event(self, event_data):
        self.add_reminder(event_data)

    def run(self):
        while True:
            self.check_reminders()
            time.sleep(60)  # Check every minute


def start_module(event_bus):
    active_reminder = ActiveReminder()
    event_bus.subscribe('TASK_SCHEDULED', active_reminder.handle_task_event)
    event_bus.emit('EMIT_SPEAK', 'Active Reminder module started and listening for task scheduling events.')
    active_reminder.run()
