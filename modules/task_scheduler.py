import os
import json
from datetime import datetime, timedelta
from threading import Thread, Event
from time import sleep
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/task_scheduler.log'

class TaskScheduler:
    def __init__(self):
        self.tasks = []
        self.stop_event = Event()
        self.load_tasks()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_tasks(self):
        try:
            with open('/home/triad/mitch/data/scheduled_tasks.json', 'r') as file:
                self.tasks = json.load(file)
                self.log_action('Tasks loaded successfully.')
        except FileNotFoundError:
            self.tasks = []
            self.log_action('No existing task file found, starting fresh.')

    def save_tasks(self):
        with open('/home/triad/mitch/data/scheduled_tasks.json', 'w') as file:
            json.dump(self.tasks, file)
            self.log_action('Tasks saved successfully.')

    def add_task(self, task_data):
        self.tasks.append(task_data)
        self.save_tasks()
        self.log_action(f'Task added: {task_data}')

    def remove_task(self, task_id):
        self.tasks = [task for task in self.tasks if task['id'] != task_id]
        self.save_tasks()
        self.log_action(f'Task removed: {task_id}')

    def check_tasks(self):
        current_time = datetime.now()
        for task in self.tasks[:]:  # Make a copy of the list for safe removal
            task_time = datetime.fromisoformat(task['time'])
            if current_time >= task_time:
                self.emit_task_reminder(task)
                self.tasks.remove(task)  # Remove task after execution
                self.save_tasks()

    def emit_task_reminder(self, task):
        reminder_message = f"Reminder: {task['description']}"
        event_bus.emit('EMIT_SPEAK', {'message': reminder_message})
        self.log_action(f'Reminder emitted for task: {task}')

    def run_scheduler(self):
        self.log_action('Task scheduler started.')
        while not self.stop_event.is_set():
            self.check_tasks()
            sleep(60)  # Check every minute

    def stop(self):
        self.stop_event.set()
        self.log_action('Task scheduler stopped.')


def start_module(event_bus):
    scheduler = TaskScheduler()
    Thread(target=scheduler.run_scheduler, daemon=True).start()

    event_bus.subscribe('ADD_TASK', scheduler.add_task)
    event_bus.subscribe('REMOVE_TASK', scheduler.remove_task)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
