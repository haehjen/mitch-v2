from core.event_bus import event_bus
from core.event_registry import IntentRegistry
import json
import os
from datetime import datetime
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("task_automator")

TASKS_FILE = f"{MITCH_ROOT}/data/tasks.json"
LOG_FILE = os.path.join(MITCH_ROOT, "logs", "innermono.log")
INJECTIONS_DIR = f"{MITCH_ROOT}/data/injections/"

class TaskAutomator:
    def __init__(self):
        self.tasks = self.load_tasks()

    def load_tasks(self):
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r') as file:
                return json.load(file)
        return []

    def save_tasks(self):
        with open(TASKS_FILE, 'w') as file:
            json.dump(self.tasks, file, indent=4)

    def add_task(self, task):
        self.tasks.append(task)
        self.save_tasks()

    def log_action(self, message):
        logger.info(str(f"{datetime.now().isoformat()} - {message}\n").rstrip("\n"))

    def inject_context(self, context):
        injection_file = os.path.join(INJECTIONS_DIR, 'task_context.json')
        with open(injection_file, 'w') as file:
            json.dump(context, file)

    def handle_create_task_event(self, data):
        task_description = data.get('text')
        task = {
            'description': task_description,
            'timestamp': datetime.now().isoformat()
        }
        self.add_task(task)
        self.log_action(f"Task created: {task_description}")
        self.inject_context({'new_task': task_description})

    def handle_list_tasks_event(self, _):
        tasks_summary = "\n".join([f"- {task['description']}" for task in self.tasks])
        self.log_action("Listing all tasks:")
        self.log_action(tasks_summary)
        event_bus.emit('TASKS_LISTED', {'tasks': self.tasks})


task_automator = TaskAutomator()

def start_module(event_bus):
    def create_task_handler(text):
        task_automator.handle_create_task_event({'text': text})

    def list_tasks_handler(_):
        task_automator.handle_list_tasks_event({})

    IntentRegistry.register_intent(
        'create_task',
        create_task_handler,
        keywords=[
            'create task',
            'add task',
            'new task',
            'set reminder',
            'remind me to',
            'add reminder',
            'todo',
            'to do',
        ],
        objects=[]
    )

    IntentRegistry.register_intent(
        'list_tasks',
        list_tasks_handler,
        keywords=[
            'show tasks',
            'list tasks',
            'current tasks',
            'show my tasks',
            'what are my tasks',
            'show reminders',
            'list reminders',
        ],
        objects=[]
    )

    event_bus.subscribe('CREATE_TASK', task_automator.handle_create_task_event)
    event_bus.subscribe('LIST_TASKS', task_automator.handle_list_tasks_event)

    task_automator.log_action("TaskAutomator module started.")
