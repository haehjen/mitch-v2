import os
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/user_engagement_tracker.log'

class UserEngagementTracker:
    def __init__(self):
        self.interaction_count = 0
        self.engagement_start = datetime.now()
        self.engagement_duration = timedelta()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_interaction(self, event_data):
        self.interaction_count += 1
        self.engagement_duration = datetime.now() - self.engagement_start
        self.log_action(f'User interaction recorded. Total interactions: {self.interaction_count}')

    def start_tracking(self):
        self.log_action('User engagement tracking started.')

    def report_engagement(self):
        report_message = {
            'total_interactions': self.interaction_count,
            'engagement_duration_minutes': self.engagement_duration.total_seconds() / 60
        }
        event_bus.emit('USER_ENGAGEMENT_REPORT', report_message)
        self.log_action(f'User engagement report emitted: {report_message}')


def start_module(event_bus):
    engagement_tracker = UserEngagementTracker()
    event_bus.subscribe('INTERACTION_EVENT', engagement_tracker.handle_interaction)
    event_bus.subscribe('REPORT_ENGAGEMENT', lambda _: engagement_tracker.report_engagement())
    engagement_tracker.start_tracking()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
