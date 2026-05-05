import os
import json
from core.event_bus import event_bus
from datetime import datetime
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("user_engagement_tracker")

ENGAGEMENT_LOG_FILE = f"{MITCH_ROOT}/logs/engagement.log"
INJECTION_FILE_PATH = f"{MITCH_ROOT}/data/injections/user_engagement.json"

class UserEngagementTracker:
    def __init__(self):
        self.interaction_count = 0
        self.last_interaction_time = None

    def log_interaction(self, data):
        self.interaction_count += 1
        self.last_interaction_time = datetime.now()

        # Log the interaction details
        with open(ENGAGEMENT_LOG_FILE, 'a') as log_file:
            log_file.write(f"Interaction logged at {self.last_interaction_time}, Details: {data}\n")

        # Save engagement data to an injection file
        self.save_engagement_data()

    def save_engagement_data(self):
        engagement_data = {
            'interaction_count': self.interaction_count,
            'last_interaction_time': self.last_interaction_time.isoformat() if self.last_interaction_time else None
        }
        with open(INJECTION_FILE_PATH, 'w') as file:
            json.dump(engagement_data, file)

    def get_engagement_metrics(self):
        last_ts = self.last_interaction_time.isoformat() if self.last_interaction_time else None
        return {
            'interaction_count': self.interaction_count,
            'last_interaction_time': last_ts,
            'engagement': self.interaction_count,
        }

user_engagement_tracker = UserEngagementTracker()

def handle_user_interaction(data):
    user_engagement_tracker.log_interaction(data)

    # Emit an event to update engagement metrics
    event_bus.emit('USER_ENGAGEMENT_UPDATED', user_engagement_tracker.get_engagement_metrics())

    # Log the update
    logger.info(str("User engagement updated.\n").rstrip("\n"))


def start_module(event_bus):
    event_bus.subscribe('EMIT_INPUT_RECEIVED', handle_user_interaction)

    # Register an intent to track user engagement
    from core.event_registry import IntentRegistry
    IntentRegistry.register_intent(
        'track_user_engagement',
        handle_user_interaction,
        keywords=['track', 'user', 'engagement', 'interaction'],
        objects=[]
    )

    # Log module startup
    logger.info(str("UserEngagementTracker module started.\n").rstrip("\n"))
