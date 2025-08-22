import threading
import time
from datetime import datetime
from core.event_bus import event_bus

class ContextualReminder:
    def __init__(self):
        self.reminders = []  # Stores all reminders
        self.running = True

    def add_reminder(self, reminder_text, reminder_time, context=None):
        """
        Adds a new reminder to the system.

        :param reminder_text: The text of the reminder
        :param reminder_time: The time to trigger the reminder (datetime object)
        :param context: Optional context to trigger the reminder
        """
        self.reminders.append({
            'reminder_text': reminder_text,
            'reminder_time': reminder_time,
            'context': context
        })
        self.log_action(f"Reminder set for {reminder_text} at {reminder_time}, context: {context}.")

    def run(self):
        while self.running:
            now = datetime.now()
            for reminder in self.reminders[:]:  # Iterate over a copy to modify the list inside the loop
                if now >= reminder['reminder_time']:
                    self.trigger_reminder(reminder)
                    self.reminders.remove(reminder)
            time.sleep(1)  # Sleep to prevent CPU overuse

    def trigger_reminder(self, reminder):
        """
        Triggers the reminder.

        :param reminder: The reminder to be triggered
        """
        event_bus.emit('EMIT_SPEAK', {'message': reminder['reminder_text']})
        self.log_action(f"Triggered reminder: {reminder['reminder_text']}")

    def stop(self):
        self.running = False

    def log_action(self, message):
        with open('/home/triad/mitch/logs/contextual_reminder.log', 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")

reminder_system = ContextualReminder()

def start_module(event_bus):
    """
    Entry point for the Contextual Reminder module.
    """
    def handle_new_reminder(event_data):
        reminder_text = event_data.get('reminder_text')
        reminder_time = event_data.get('reminder_time')
        context = event_data.get('context')
        reminder_system.add_reminder(reminder_text, reminder_time, context)

    event_bus.subscribe('set_reminder', handle_new_reminder)
    reminder_thread = threading.Thread(target=reminder_system.run)
    reminder_thread.start()
