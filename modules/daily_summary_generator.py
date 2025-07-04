import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/daily_summary_generator.log'
SUMMARY_FILE = '/home/triad/mitch/data/daily_summary.json'

class DailySummaryGenerator:
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(days=1)
        self.activities = []
        self.insights = []
        
    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_activity_event(self, event_data):
        # Record user activities or system events
        self.activities.append(event_data)
        self.log_action(f'Activity recorded: {event_data}')

    def handle_insight_event(self, event_data):
        # Record insights generated during the day
        self.insights.append(event_data)
        self.log_action(f'Insight recorded: {event_data}')

    def generate_summary(self):
        # Compile a daily summary
        summary = {
            'date': self.start_time.date().isoformat(),
            'activities': self.activities,
            'insights': self.insights
        }
        self.save_summary(summary)
        self.log_action('Daily summary generated.')

    def save_summary(self, summary):
        with open(SUMMARY_FILE, 'w') as file:
            json.dump(summary, file)
            self.log_action('Summary saved successfully.')

    def start(self):
        self.log_action('Daily summary generation started.')
        # You could implement a mechanism to generate summary at the end of the day
        # using a scheduler or another mechanism within MITCH.


def start_module(event_bus):
    summary_generator = DailySummaryGenerator()
    event_bus.subscribe('ACTIVITY_EVENT', summary_generator.handle_activity_event)
    event_bus.subscribe('INSIGHT_EVENT', summary_generator.handle_insight_event)
    summary_generator.start()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
