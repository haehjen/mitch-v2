import datetime
import json
import os
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/time_management.log'
TASKS_FILE = '/home/triad/mitch/data/tasks.json'

class TimeManagement:
    def __init__(self):
        self.tasks = self.load_tasks()

    def load_tasks(self):
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r') as file:
                return json.load(file)
        return []

    def save_tasks(self):
        with open(TASKS_FILE, 'w') as file:
            json.dump(self.tasks, file)

    def handle_schedule_task(self, event_data):
        task = {
            'description': event_data['description'],
            'time': event_data['time'],
            'notified': False
        }
        self.tasks.append(task)
        self.save_tasks()
        self.log(f"Scheduled new task: {task['description']} at {task['time']}")

    def check_tasks(self):
        now = datetime.datetime.now().isoformat()
        for task in self.tasks:
            if not task['notified'] and task['time'] <= now:
                event_bus.emit('task_due', task)
                task['notified'] = True
                self.log(f"Task due: {task['description']} at {task['time']}")
        self.save_tasks()

    def log(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f"{datetime.datetime.now().isoformat()} - {message}\n")


def start_module(event_bus):
    time_manager = TimeManagement()
    event_bus.subscribe('schedule_task', time_manager.handle_schedule_task)

    def periodic_task_check():
        time_manager.check_tasks()
        
    event_bus.subscribe('tick_one_minute', lambda _: periodic_task_check())
    time_manager.log("Time Management module started.")
