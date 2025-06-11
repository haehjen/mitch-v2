import os
import json
from core.event_bus import event_bus, INNERMONO_PATH
from datetime import datetime

LOG_FILE_PATH = INNERMONO_PATH

class DynamicTaskOptimizer:
    def __init__(self):
        self.task_queue = []
        self.resource_usage = {'cpu': 0, 'memory': 0, 'disk': 0}

    def log_action(self, action_data):
        """Log actions to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(action_data) + '\n')

    def handle_task_event(self, event_data):
        """Handle task scheduling events."""
        task = event_data.get('task')
        self.task_queue.append(task)
        self.optimize_task_priority()

    def handle_resource_event(self, event_data):
        """Handle system resource usage events."""
        self.resource_usage['cpu'] = event_data.get('cpu_usage', 0)
        self.resource_usage['memory'] = event_data.get('memory_usage', 0)
        self.resource_usage['disk'] = event_data.get('disk_usage', 0)
        self.optimize_task_priority()

    def optimize_task_priority(self):
        """Optimize priorities based on resource usage and task urgency."""
        for task in self.task_queue:
            task['priority'] = self.calculate_priority(task)
        self.task_queue.sort(key=lambda x: x['priority'], reverse=True)
        self.log_action({
            'timestamp': datetime.now().isoformat(),
            'optimized_queue': self.task_queue
        })

    def calculate_priority(self, task):
        """Calculate task priority based on urgency and resource usage."""
        urgency_factor = task.get('urgency', 1)
        cpu_factor = 1 - self.resource_usage['cpu'] / 100
        memory_factor = 1 - self.resource_usage['memory'] / 100
        return urgency_factor * (cpu_factor + memory_factor) / 2

    def handle_execution_request(self, event_data):
        """Execute the highest priority task."""
        if self.task_queue:
            highest_priority_task = self.task_queue.pop(0)
            event_bus.emit('EXECUTE_TASK', highest_priority_task)
            self.log_action({
                'timestamp': datetime.now().isoformat(),
                'executed_task': highest_priority_task
            })


def start_module(event_bus):
    optimizer = DynamicTaskOptimizer()
    event_bus.subscribe('TASK_SCHEDULED', optimizer.handle_task_event)
    event_bus.subscribe('RESOURCE_USAGE_UPDATE', optimizer.handle_resource_event)
    event_bus.subscribe('REQUEST_TASK_EXECUTION', optimizer.handle_execution_request)
    
    print('Dynamic Task Optimizer module started and listening for scheduling and resource usage events.')
