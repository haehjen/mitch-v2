import os
import json
import logging
from core.event_bus import event_bus
from threading import Thread, Event
from time import sleep, time
from datetime import datetime
from core.peterjones import get_logger

logger = get_logger("TaskScheduler")

class TaskScheduler:
    def __init__(self):
        self.tasks = []
        self.stop_event = Event()
        self.injections_dir = "/home/triad/mitch/data/injections"
        self.thread = Thread(target=self.run)
        self.thread.daemon = True

    def schedule_task(self, task_name, interval, action):
        """Schedule a task to run every `interval` seconds."""
        task = {
            'name': task_name,
            'interval': interval,
            'action': action,
            'last_run': 0
        }
        self.tasks.append(task)
        logger.info(f"[TaskScheduler] Scheduled task '{task_name}' every {interval} seconds.")

    def run(self):
        """Main loop to run tasks at intervals."""
        while not self.stop_event.is_set():
            current_time = time()
            for task in self.tasks:
                if current_time - task['last_run'] >= task['interval']:
                    logger.info(f"[TaskScheduler] Executing task: {task['name']}")
                    try:
                        task['action']()
                        task['last_run'] = current_time
                    except Exception as e:
                        logger.error(f"[TaskScheduler] Error in task '{task['name']}': {e}")
            sleep(1)

    def save_task_context(self):
        """Save a snapshot of current task schedule to injection."""
        context = {
            'timestamp': datetime.utcnow().isoformat(),
            'tasks': [{'name': t['name'], 'interval': t['interval']} for t in self.tasks]
        }
        try:
            os.makedirs(self.injections_dir, exist_ok=True)
            path = os.path.join(self.injections_dir, "task_schedule.json")
            with open(path, "w") as f:
                json.dump(context, f, indent=2)
            logger.info("[TaskScheduler] Saved task schedule to injection.")
        except Exception as e:
            logger.error(f"[TaskScheduler] Failed to save task context: {e}")

    def shutdown(self):
        """Stop scheduler thread cleanly."""
        self.stop_event.set()
        self.thread.join()
        logger.info("[TaskScheduler] Scheduler stopped.")

    def handle_shutdown_event(self, event_data):
        self.shutdown()

def start_module(event_bus):
    scheduler = TaskScheduler()

    # Subscribe to shutdown
    event_bus.subscribe("SHUTDOWN", scheduler.handle_shutdown_event)

    # Periodic emit task
    def heartbeat():
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "alive",
            "source": "task_scheduler"
        }
        event_bus.emit("ECHO_HEARTBEAT", payload)
        logger.debug("[TaskScheduler] Emitted ECHO_HEARTBEAT.")

    # Schedule tasks
    scheduler.schedule_task("Heartbeat", 10, heartbeat)
    scheduler.schedule_task("Save Schedule", 120, scheduler.save_task_context)
    scheduler.schedule_task("Log Maintenance", 3600, lambda: logger.info("Performing log maintenance."))

    scheduler.thread.start()
    logger.info("[TaskScheduler] Module started.")
