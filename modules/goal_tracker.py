import json
from datetime import datetime
from core.event_bus import event_bus

class GoalTracker:
    def __init__(self):
        self.goals = self.load_goals()

    def load_goals(self):
        try:
            with open('/home/triad/mitch/data/goals.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_goals(self):
        with open('/home/triad/mitch/data/goals.json', 'w') as file:
            json.dump(self.goals, file, indent=4)

    def add_goal(self, goal_name, due_date):
        goal = {
            'goal_name': goal_name,
            'due_date': due_date,
            'created_at': datetime.now().isoformat(),
            'completed': False
        }
        self.goals.append(goal)
        self.save_goals()
        self.log_action(f"Goal added: {goal_name} with due date {due_date}.")

    def complete_goal(self, goal_name):
        for goal in self.goals:
            if goal['goal_name'] == goal_name and not goal['completed']:
                goal['completed'] = True
                self.save_goals()
                self.log_action(f"Goal completed: {goal_name}.")
                return
        self.log_action(f"Goal not found or already completed: {goal_name}.")

    def list_goals(self):
        active_goals = [goal for goal in self.goals if not goal['completed']]
        return active_goals

    def log_action(self, message):
        with open('/home/triad/mitch/logs/goal_tracker.log', 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")


goal_tracker = GoalTracker()

def handle_add_goal(event_data):
    goal_name = event_data.get('goal_name')
    due_date = event_data.get('due_date')
    goal_tracker.add_goal(goal_name, due_date)


def handle_complete_goal(event_data):
    goal_name = event_data.get('goal_name')
    goal_tracker.complete_goal(goal_name)


def handle_list_goals(event_data):
    active_goals = goal_tracker.list_goals()
    event_bus.emit('EMIT_GOAL_LIST', active_goals)


def start_module(event_bus):
    event_bus.subscribe('add_goal', handle_add_goal)
    event_bus.subscribe('complete_goal', handle_complete_goal)
    event_bus.subscribe('list_goals', handle_list_goals)
