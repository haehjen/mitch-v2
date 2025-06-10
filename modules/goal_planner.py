import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/goal_planner.log'

class GoalPlanner:
    def __init__(self):
        self.goals = []
        self.load_goals()

    def load_goals(self):
        """Load goals from a persistent storage."""
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r') as file:
                self.goals = json.load(file)
        else:
            self.goals = []

    def save_goals(self):
        """Save the current state of goals to persistent storage."""
        with open(LOG_FILE_PATH, 'w') as file:
            json.dump(self.goals, file)

    def add_goal(self, event_data):
        """Add a new goal."""
        goal = {
            'id': len(self.goals) + 1,
            'description': event_data.get('description'),
            'deadline': event_data.get('deadline'),
            'completed': False
        }
        self.goals.append(goal)
        self.save_goals()
        self.log_action(f"Added new goal: {goal['description']}")

    def complete_goal(self, event_data):
        """Mark a goal as completed."""
        goal_id = event_data.get('goal_id')
        for goal in self.goals:
            if goal['id'] == goal_id:
                goal['completed'] = True
                self.save_goals()
                self.log_action(f"Completed goal: {goal['description']}")
                break

    def remove_goal(self, event_data):
        """Remove a goal by ID."""
        goal_id = event_data.get('goal_id')
        self.goals = [goal for goal in self.goals if goal['id'] != goal_id]
        self.save_goals()
        self.log_action(f"Removed goal with ID: {goal_id}")

    def list_goals(self, event_data):
        """Emit a list of current goals."""
        event_bus.emit('EMIT_GOAL_LIST', {'goals': self.goals})

    def log_action(self, message):
        """Log important actions."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}\n"
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(log_entry)


def start_module(event_bus):
    goal_planner = GoalPlanner()
    event_bus.subscribe('ADD_GOAL', goal_planner.add_goal)
    event_bus.subscribe('COMPLETE_GOAL', goal_planner.complete_goal)
    event_bus.subscribe('REMOVE_GOAL', goal_planner.remove_goal)
    event_bus.subscribe('LIST_GOALS', goal_planner.list_goals)
    
    print('Goal Planner module started and listening for goal-related events.')
