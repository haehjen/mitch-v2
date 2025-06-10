import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/collaborative_task_manager.log'

class CollaborativeTaskManager:
    def __init__(self):
        self.tasks = {}

    def log_task(self, task_data):
        """Log the task details."""
        timestamp = datetime.now().isoformat()
        task_data['timestamp'] = timestamp
        self.tasks[task_data['task_id']] = task_data
        self._write_log(task_data)

    def _write_log(self, data):
        """Write the task data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def handle_task_event(self, event_data):
        """Handle task-related events emitted by other modules."""
        self.log_task(event_data)

    def get_task_summary(self):
        """Summarize the tasks managed by this module."""
        summary = {}
        for task_id, task_data in self.tasks.items():
            summary[task_id] = {
                'description': task_data.get('description', 'No description'),
                'status': task_data.get('status', 'unknown')
            }
        return summary

    def handle_task_completion(self, event_data):
        """Handle task completion events and update task status."""
        task_id = event_data.get('task_id')
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = 'completed'
            self._write_log(self.tasks[task_id])


def start_module(event_bus):
    task_manager = CollaborativeTaskManager()
    event_bus.subscribe('EMIT_TASK_CREATED', task_manager.handle_task_event)
    event_bus.subscribe('EMIT_TASK_COMPLETED', task_manager.handle_task_completion)
    
    print('Collaborative Task Manager module started and listening for task events.')
