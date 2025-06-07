import os
import json
import datetime
import threading
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

logger = get_logger("task_scheduler")

LOG_FILE_PATH = os.path.join(MITCH_ROOT, 'logs', 'task_scheduler.log')

class TaskScheduler:
    def __init__(self):
        self.tasks = []
        self._load_tasks()

    def _load_tasks(self):
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r') as log_file:
                try:
                    self.tasks = json.load(log_file)
                except json.JSONDecodeError:
                    self.tasks = []

    def _save_tasks(self):
        with open(LOG_FILE_PATH, 'w') as log_file:
            json.dump(self.tasks, log_file)

    def schedule_task(self, event_data):
        task = {
            'time': event_data.get('time'),
            'interval': event_data.get('interval'),
            'action': event_data.get('action')
        }
        self.tasks.append(task)
        self._save_tasks()
        self._log(f"Scheduled task: {task}")
        self._start_task(task)

    def _log(self, message):
        logger.info(message)

    def _start_task(self, task):
        def execute_task():
            if task['interval']:
                threading.Timer(task['interval'], execute_task).start()
            event_bus.emit(task['action'], {})
            self._log(f"Executed task: {task}")

        # Calculate initial delay
        if task['time']:
            now = datetime.datetime.now()
            task_time = datetime.datetime.strptime(task['time'], "%H:%M")
            initial_delay = (task_time - now).total_seconds()
            if initial_delay < 0:
                initial_delay += 86400  # Schedule for the next day
            threading.Timer(initial_delay, execute_task).start()
        else:
            execute_task()

    def handle_schedule_event(self, event_data):
        self.schedule_task(event_data)


def start_module(event_bus):
    task_scheduler = TaskScheduler()
    event_bus.subscribe('SCHEDULE_TASK', task_scheduler.handle_schedule_event)
    logger.info('Task Scheduler module started and listening for task scheduling events.')
