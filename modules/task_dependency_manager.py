import os
import json
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/task_dependency_manager.log'

class TaskDependencyManager:
    def __init__(self):
        self.task_dependencies = {}
        self.completed_tasks = set()

    def log(self, message):
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(f'{message}\n')

    def add_task_dependency(self, task, dependencies):
        """Add a task and its dependencies."""
        self.task_dependencies[task] = dependencies
        self.log(f'Added task: {task} with dependencies: {dependencies}')

    def complete_task(self, task):
        """Mark a task as completed."""
        self.completed_tasks.add(task)
        self.log(f'Task completed: {task}')

    def can_execute_task(self, task):
        """Check if a task can be executed."""
        if task not in self.task_dependencies:
            return True
        dependencies = self.task_dependencies[task]
        can_execute = all(dep in self.completed_tasks for dep in dependencies)
        self.log(f'Can execute task {task}: {can_execute}')
        return can_execute

    def handle_task_event(self, event_data):
        """Handle task-related events."""
        task = event_data.get('task')
        action = event_data.get('action')
        if action == 'add':
            dependencies = event_data.get('dependencies', [])
            self.add_task_dependency(task, dependencies)
        elif action == 'complete':
            self.complete_task(task)
        elif action == 'check':
            can_execute = self.can_execute_task(task)
            event_bus.emit('TASK_EXECUTION_VALIDATION', {'task': task, 'can_execute': can_execute})


def start_module(event_bus):
    task_dependency_manager = TaskDependencyManager()
    event_bus.subscribe('TASK_EVENT', task_dependency_manager.handle_task_event)
    print('Task Dependency Manager module started and listening for task events.')
