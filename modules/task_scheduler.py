import threading
import time
from datetime import datetime, timedelta
from core.event_bus import event_bus

class TaskScheduler:
    def __init__(self):
        self.tasks = []  # List to store scheduled tasks
        self.running = True

    def add_task(self, task_name, task_time, event_name, data):
        """
        Schedule a new task.

        :param task_name: Name of the task
        :param task_time: Time to execute the task (datetime object)
        :param event_name: Event to emit when the task is executed
        :param data: Data to send with the event
        """
        self.tasks.append({
            'task_name': task_name,
            'task_time': task_time,
            'event_name': event_name,
            'data': data
        })
        self.log_action(f"Scheduled task '{task_name}' for {task_time}.")

    def run(self):
        while self.running:
            now = datetime.now()
            for task in self.tasks[:]:  # Iterate over a copy to modify the list inside the loop
                if now >= task['task_time']:
                    event_bus.emit(task['event_name'], task['data'])
                    self.log_action(f"Executed task '{task['task_name']}' at {now}.")
                    self.tasks.remove(task)
            time.sleep(1)  # Sleep to prevent CPU overuse

    def stop(self):
        self.running = False

    def log_action(self, message):
        with open('/home/triad/mitch/logs/task_scheduler.log', 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")

scheduler = TaskScheduler()

def start_module(event_bus):
    """
    Entry point for the Task Scheduler module.
    """
    def handle_new_task(event_data):
        task_name = event_data.get('task_name')
        task_time = event_data.get('task_time')
        event_name = event_data.get('event_name')
        data = event_data.get('data')
        scheduler.add_task(task_name, task_time, event_name, data)

    event_bus.subscribe('schedule_task', handle_new_task)
    scheduler_thread = threading.Thread(target=scheduler.run)
    scheduler_thread.start()