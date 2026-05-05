import json
import os
from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("habit_inspector")

HABIT_DATA_FILE = f"{MITCH_ROOT}/data/habit_data.json"

class HabitInspector:
    def __init__(self):
        self.habits = self.load_habits()

    def load_habits(self):
        if os.path.exists(HABIT_DATA_FILE):
            with open(HABIT_DATA_FILE, 'r') as file:
                return json.load(file)
        return {}

    def save_habits(self):
        with open(HABIT_DATA_FILE, 'w') as file:
            json.dump(self.habits, file)

    def analyze_habits(self):
        # Analyze habits and identify patterns
        insights = {habit: self.habits[habit] for habit in self.habits if self.habits[habit] > 5}
        return insights

    def update_habit(self, habit_name):
        if habit_name in self.habits:
            self.habits[habit_name] += 1
        else:
            self.habits[habit_name] = 1
        self.save_habits()

    def clear_habits(self):
        self.habits = {}
        self.save_habits()

habit_inspector = HabitInspector()

def handle_log_habit_event(data):
    # Update habit based on event data
    habit_name = data.get('habit_name')
    if habit_name:
        habit_inspector.update_habit(habit_name)
        
        # Log the habit update
        logger.info(str(f"Updated habit: {habit_name}\n").rstrip("\n"))

    # Emit a habit updated event
    event_bus.emit('HABIT_UPDATED', {'habit_name': habit_name})

def handle_analyze_habits_event(data):
    # Analyze habits and emit insights
    insights = habit_inspector.analyze_habits()
    
    # Log the insights
    logger.info(str(f"Habit insights: {insights}\n").rstrip("\n"))

    # Emit an event with the insights
    event_bus.emit('HABIT_INSIGHTS', insights)

def start_module(event_bus):
    event_bus.subscribe('LOG_HABIT', handle_log_habit_event)
    event_bus.subscribe('ANALYZE_HABITS', handle_analyze_habits_event)

    # Register intents for logging and analyzing habits
    IntentRegistry.register_intent(
        'log_habit',
        handle_log_habit_event,
        keywords=['log habit', 'track habit', 'record habit'],
        objects=[]
    )
    
    IntentRegistry.register_intent(
        'analyze_habits',
        handle_analyze_habits_event,
        keywords=['analyze habits', 'habit insights', 'habit patterns'],
        objects=[]
    )

    # Log module startup
    logger.info(str("HabitInspector module started.\n").rstrip("\n"))
