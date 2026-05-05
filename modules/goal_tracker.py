import os
import json
from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("goal_tracker")

GOAL_TRACKER_FILE = f"{MITCH_ROOT}/data/goals.json"

class GoalTracker:
    def __init__(self):
        self.goals = self.load_goals()

    def load_goals(self):
        if os.path.exists(GOAL_TRACKER_FILE):
            with open(GOAL_TRACKER_FILE, 'r') as file:
                return json.load(file)
        return {}

    def save_goals(self):
        with open(GOAL_TRACKER_FILE, 'w') as file:
            json.dump(self.goals, file)

    def set_goal(self, goal_name, target):
        self.goals[goal_name] = {'target': target, 'progress': 0}
        self.save_goals()

    def update_progress(self, goal_name, progress):
        if goal_name in self.goals:
            self.goals[goal_name]['progress'] += progress
            self.save_goals()

    def get_status(self):
        return self.goals

    def clear_goals(self):
        self.goals = {}
        self.save_goals()

    def log_action(self, message):
        logger.info(str(message + '\n').rstrip("\n"))

    def emit_goal_update(self, data):
        event_bus.emit('GOAL_UPDATE', data)

    def emit_goal_status(self, data):
        event_bus.emit('GOAL_STATUS', data)

    def handle_set_goal_event(self, data):
        goal_name = data.get('goal_name')
        target = data.get('target', 0)
        self.set_goal(goal_name, target)
        self.log_action(f'Set new goal: {goal_name} with target {target}')
        self.emit_goal_update({'goal': goal_name, 'target': target})

    def handle_update_progress_event(self, data):
        goal_name = data.get('goal_name')
        progress = data.get('progress', 0)
        self.update_progress(goal_name, progress)
        self.log_action(f'Updated goal: {goal_name} with progress {progress}')
        self.emit_goal_update({'goal': goal_name, 'progress': progress})

    def handle_get_status_event(self, data):
        status = self.get_status()
        self.log_action('Retrieved goal status')
        self.emit_goal_status(status)

    def handle_clear_goals_event(self, data):
        self.clear_goals()
        self.log_action('Cleared all goals')


goal_tracker = GoalTracker()

def start_module(event_bus):
    event_bus.subscribe('SET_GOAL', goal_tracker.handle_set_goal_event)
    event_bus.subscribe('UPDATE_PROGRESS', goal_tracker.handle_update_progress_event)
    event_bus.subscribe('GET_GOAL_STATUS', goal_tracker.handle_get_status_event)
    event_bus.subscribe('CLEAR_GOALS', goal_tracker.handle_clear_goals_event)

    IntentRegistry.register_intent(
        'set_goal',
        goal_tracker.handle_set_goal_event,
        keywords=['set goal', 'define goal', 'create goal'],
        objects=[]
    )

    IntentRegistry.register_intent(
        'update_progress',
        goal_tracker.handle_update_progress_event,
        keywords=['update progress', 'add progress', 'log progress'],
        objects=[]
    )

    IntentRegistry.register_intent(
        'get_goal_status',
        goal_tracker.handle_get_status_event,
        keywords=['goal status', 'check goals', 'goal update'],
        objects=[]
    )

    IntentRegistry.register_intent(
        'clear_goals',
        goal_tracker.handle_clear_goals_event,
        keywords=['clear goals', 'reset goals', 'delete goals'],
        objects=[]
    )

    logger.info(str('GoalTracker module started.\n').rstrip("\n"))
