import random
from core.event_bus import event_bus
from datetime import datetime

# List of motivational messages and productivity tips
MOTIVATIONAL_MESSAGES = [
    "Keep pushing forward, you're doing great!",
    "Every step counts, keep moving forward.",
    "Remember, progress, not perfection.",
    "Stay positive and keep striving for excellence!",
    "Believe in yourself, you are capable of amazing things!"
]

PRODUCTIVITY_TIPS = [
    "Break your tasks into smaller, manageable parts.",
    "Set clear, achievable goals for today.",
    "Take regular breaks to maintain focus.",
    "Prioritize your most important tasks.",
    "Eliminate distractions to boost productivity."
]

class UserMotivationBooster:
    def __init__(self):
        self.last_interaction_time = None

    def handle_user_interaction(self, event_data):
        """
        Handles user interaction events to determine when to send motivational messages.

        :param event_data: Data related to user interaction events
        """
        self.last_interaction_time = datetime.now()
        if self.should_send_motivation():
            self.send_motivation()

    def should_send_motivation(self):
        """
        Determines if it's an appropriate time to send a motivational message.

        :return: True if a message should be sent, otherwise False
        """
        if self.last_interaction_time:
            elapsed_time = datetime.now() - self.last_interaction_time
            # Check if more than an hour has passed since the last interaction
            return elapsed_time.total_seconds() > 3600
        return True

    def send_motivation(self):
        """
        Sends a random motivational message or productivity tip to the user.
        """
        message = random.choice(MOTIVATIONAL_MESSAGES + PRODUCTIVITY_TIPS)
        log_message = f"Sending motivational message: {message}"
        self.log_action(log_message)
        event_bus.emit('EMIT_SPEAK', {'message': message})

    def log_action(self, message):
        """
        Logs actions performed by the module.

        :param message: The message to log
        """
        with open('/home/triad/mitch/logs/user_motivation_booster.log', 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")

motivation_booster = UserMotivationBooster()

def start_module(event_bus):
    """
    Entry point for the User Motivation Booster module.
    """
    event_bus.subscribe('user_interaction', motivation_booster.handle_user_interaction)
