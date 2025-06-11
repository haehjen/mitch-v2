import logging
from datetime import datetime, timedelta
from core.event_bus import event_bus

# Set up logging
logging.basicConfig(filename='/home/triad/mitch/logs/scheduled_tasks.log', level=logging.INFO)

class ScheduledTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, name, event_name, event_data, run_at):
        """
        Add a new task to be executed at a specific time.

        Args:
            name (str): The name of the task.
            event_name (str): The name of the event to emit.
            event_data (dict): The data to pass to the event.
            run_at (datetime): The time to run the task.
        """
        task = {
            'name': name,
            'event_name': event_name,
            'event_data': event_data,
            'run_at': run_at
        }
        self.tasks.append(task)
        logging.info(f"Task added: {task}")

    def remove_task(self, name):
        """Remove a task by its name."""
        self.tasks = [task for task in self.tasks if task['name'] != name]
        logging.info(f"Task removed: {name}")

    def check_tasks(self):
        """Check and execute tasks that are scheduled to run."""
        now = datetime.now()
        for task in list(self.tasks):
            if task['run_at'] <= now:
                event_bus.emit(task['event_name'], task['event_data'])
                logging.info(f"Task executed: {task}")
                self.tasks.remove(task)

# Instantiate the ScheduledTasks manager
scheduled_tasks_manager = ScheduledTasks()

def handle_time_tick(event_data):
    """
    Event handler for periodic time ticks to check for scheduled tasks.

    Args:
        event_data (dict): The event data, containing current time information.
    """
    scheduled_tasks_manager.check_tasks()

# Example usage
# scheduled_tasks_manager.add_task('Daily Check', 'EMIT_DAILY_REPORT', {}, datetime.now() + timedelta(minutes=1))

def start_module(event_bus):
    """
    Entry point for the scheduled tasks module.
    Subscribes to the time tick event to regularly check and run scheduled tasks.
    """
    event_bus.subscribe('TIME_TICK', handle_time_tick)
    logging.info('Scheduled Tasks Module started.')
