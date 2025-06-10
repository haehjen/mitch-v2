import datetime
import json
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/time_management_assistant.log'

class TimeManagementAssistant:
    def __init__(self):
        self.reminders = []

    def set_reminder(self, event_data):
        """Set a reminder based on event data."""
        reminder_time = event_data.get('time')
        task = event_data.get('task')
        self.reminders.append({'time': reminder_time, 'task': task})
        self._log(f"Reminder set for {task} at {reminder_time}")

    def check_reminders(self):
        """Check for reminders that need to be triggered."""
        current_time = datetime.datetime.now().strftime('%H:%M')
        for reminder in self.reminders:
            if reminder['time'] == current_time:
                self._notify_user(reminder['task'])

    def _notify_user(self, task):
        """Notify the user about a task."""
        event_bus.emit('EMIT_SPEAK', {'message': f'Reminder: {task}'})
        self._log(f"Notified user about task: {task}")

    def analyze_time_usage(self, event_data):
        """Analyze the user's time usage and suggest improvements."""
        # Assume event_data contains time usage patterns
        time_usage = event_data.get('time_usage')
        suggestions = self._generate_suggestions(time_usage)
        event_bus.emit('EMIT_SPEAK', {'message': f'Time Management Tips: {suggestions}'})
        self._log(f"Time usage analyzed. Suggestions: {suggestions}")

    def _generate_suggestions(self, time_usage):
        """Generate suggestions based on time usage."""
        # Placeholder for real analysis logic
        if time_usage['work'] > 8:
            return 'Consider taking more breaks during work hours.'
        elif time_usage['leisure'] < 2:
            return 'Make time for leisure activities to reduce stress.'
        else:
            return 'Your time management looks balanced!'

    def _log(self, message):
        """Log messages to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(f"{datetime.datetime.now().isoformat()} - {message}\n")


def start_module(event_bus):
    time_management_assistant = TimeManagementAssistant()
    event_bus.subscribe('SET_REMINDER', time_management_assistant.set_reminder)
    event_bus.subscribe('CHECK_REMINDERS', lambda _: time_management_assistant.check_reminders())
    event_bus.subscribe('ANALYZE_TIME_USAGE', time_management_assistant.analyze_time_usage)
    
    print('Time Management Assistant module started and listening for events.')
