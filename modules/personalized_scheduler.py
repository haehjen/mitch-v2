import json
import os
from datetime import datetime, timedelta
from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("personalized_scheduler")

SCHEDULE_FILE = f"{MITCH_ROOT}/data/scheduled_tasks.json"
INJECTION_FILE = f"{MITCH_ROOT}/data/injections/personalized_scheduler_injection.json"
LOG_FILE = os.path.join(MITCH_ROOT, "logs", "innermono.log")

class PersonalizedScheduler:
    def __init__(self):
        self.tasks = self.load_tasks()

    def load_tasks(self):
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r') as file:
                return json.load(file)
        return {}

    def save_tasks(self):
        with open(SCHEDULE_FILE, 'w') as file:
            json.dump(self.tasks, file)

    def suggest_task(self, task_name, preferred_time):
        now = datetime.now()
        suggestion_time = now + timedelta(minutes=preferred_time)
        self.tasks[task_name] = suggestion_time.strftime('%Y-%m-%d %H:%M:%S')
        self.save_tasks()
        self.log_action(f"Suggested task '{task_name}' at {suggestion_time}")
        self.emit_injection(task_name, suggestion_time)

    def emit_injection(self, task_name, suggestion_time):
        injection_data = {
            "task": task_name,
            "suggested_time": suggestion_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(INJECTION_FILE, 'w') as file:
            json.dump(injection_data, file)

    def log_action(self, message):
        logger.info(str(f"{datetime.now().isoformat()} [PersonalizedScheduler] {message}\n").rstrip("\n"))

scheduler = PersonalizedScheduler()

def handle_user_activity(data):
    # Analyze user activity and suggest tasks accordingly
    if 'activity' in data:
        activity = data['activity']
        if activity == 'workout':
            scheduler.suggest_task('Stretching', 30)
        elif activity == 'meeting':
            scheduler.suggest_task('Follow-up Email', 15)

    scheduler.log_action(f"Handled user activity: {data}")


def start_module(event_bus):
    event_bus.subscribe('USER_ACTIVITY', handle_user_activity)

    # Register an intent for manual task suggestion
    def manual_task_suggestion_handler(text):
        task_name = 'Manual Task'
        scheduler.suggest_task(task_name, 60)

    IntentRegistry.register_intent(
        'manual_task_suggestion',
        manual_task_suggestion_handler,
        keywords=['suggest', 'task', 'schedule'],
        objects=[]
    )

    # Log module startup
    scheduler.log_action("PersonalizedScheduler module started.")