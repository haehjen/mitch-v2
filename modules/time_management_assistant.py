import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/time_management_assistant.log'
DATA_FILE = '/home/triad/mitch/data/time_spent.json'

class TimeManagementAssistant:
    def __init__(self):
        self.time_spent = {}
        self.load_time_data()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_time_data(self):
        try:
            with open(DATA_FILE, 'r') as file:
                self.time_spent = json.load(file)
                self.log_action('Time data loaded successfully.')
        except FileNotFoundError:
            self.time_spent = {}
            self.log_action('No existing time data file found, starting fresh.')

    def save_time_data(self):
        with open(DATA_FILE, 'w') as file:
            json.dump(self.time_spent, file)
            self.log_action('Time data saved successfully.')

    def start_task(self, task_name):
        if task_name not in self.time_spent:
            self.time_spent[task_name] = {'total': 0, 'start': datetime.now().isoformat()}
        else:
            self.time_spent[task_name]['start'] = datetime.now().isoformat()
        self.log_action(f'Task started: {task_name}')

    def stop_task(self, task_name):
        if task_name in self.time_spent and 'start' in self.time_spent[task_name]:
            start_time = datetime.fromisoformat(self.time_spent[task_name]['start'])
            time_spent = (datetime.now() - start_time).total_seconds() / 60  # Time spent in minutes
            self.time_spent[task_name]['total'] += time_spent
            del self.time_spent[task_name]['start']
            self.log_action(f'Task stopped: {task_name}, Time spent: {time_spent:.2f} minutes')
            self.save_time_data()

    def report_time_spent(self):
        report = 'Time Spent Report:\n'
        for task, data in self.time_spent.items():
            report += f"- {task}: {data['total']:.2f} minutes\n"
        event_bus.emit('EMIT_SPEAK', {'message': report})
        self.log_action('Time spent report emitted.')


def start_module(event_bus):
    time_manager = TimeManagementAssistant()

    event_bus.subscribe('START_TASK', time_manager.start_task)
    event_bus.subscribe('STOP_TASK', time_manager.stop_task)
    event_bus.subscribe('REPORT_TIME_SPENT', time_manager.report_time_spent)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
