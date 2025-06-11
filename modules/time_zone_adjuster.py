import os
import json
from datetime import datetime, timezone, timedelta
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class TimeZoneAdjuster:
    def __init__(self):
        self.current_time_zone = timezone.utc
        self.tasks = []

    def log(self, message):
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()}: {message}\n')

    def adjust_task_times(self, event_data):
        """Adjusts task times based on the current time zone."""
        for task in self.tasks:
            original_time = task['time']
            adjusted_time = original_time.astimezone(self.current_time_zone)
            task['adjusted_time'] = adjusted_time
            self.log(f"Adjusted task '{task['name']}' from {original_time} to {adjusted_time}")

    def update_time_zone(self, event_data):
        """Updates the current time zone based on event data."""
        self.current_time_zone = event_data.get('new_time_zone', timezone.utc)
        self.log(f"Updated time zone to {self.current_time_zone}")
        self.adjust_task_times({})

    def add_task(self, event_data):
        """Adds a new task to the schedule."""
        task_name = event_data.get('task_name')
        task_time = event_data.get('task_time', datetime.now(timezone.utc))
        task = {
            'name': task_name,
            'time': task_time
        }
        self.tasks.append(task)
        self.log(f"Added task '{task_name}' at {task_time}")
        self.adjust_task_times({})


def start_module(event_bus):
    time_zone_adjuster = TimeZoneAdjuster()
    event_bus.subscribe('NEW_TASK_ADDED', time_zone_adjuster.add_task)
    event_bus.subscribe('TIME_ZONE_UPDATED', time_zone_adjuster.update_time_zone)
    
    print('Time Zone Adjuster module started and listening for task and time zone update events.')
