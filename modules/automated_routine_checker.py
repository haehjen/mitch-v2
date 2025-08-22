import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

class AutomatedRoutineChecker:
    def __init__(self):
        self.log_file_path = '/home/triad/mitch/logs/automated_routine_checker.log'
        self.feedback_file_path = '/home/triad/mitch/data/user_feedback.json'

    def analyze_logs_and_feedback(self):
        try:
            routine_issues = []

            # Analyze task scheduler log
            task_log_path = '/home/triad/mitch/logs/task_scheduler.log'
            if os.path.exists(task_log_path):
                with open(task_log_path, 'r') as log_file:
                    for line in log_file.readlines():
                        if 'Executed task' in line:
                            exec_time_str = line.split('at ')[-1].strip()
                            exec_time = datetime.strptime(exec_time_str, "%Y-%m-%d %H:%M:%S.%f")
                            if exec_time.hour < 6 or exec_time.hour > 22:
                                routine_issues.append(f"Task executed at odd hour: {exec_time}")

            # Analyze feedback data
            if os.path.exists(self.feedback_file_path):
                with open(self.feedback_file_path, 'r') as feedback_file:
                    feedback_data = json.load(feedback_file)
                    for feedback in feedback_data.get('feedback', []):
                        if 'delay' in feedback.get('content', '').lower():
                            routine_issues.append(f"User reported delay: {feedback.get('content')}")

            # Log findings
            for issue in routine_issues:
                self.log_action(issue)

            # Emit analysis results
            if routine_issues:
                event_bus.emit('routine_analysis_complete', {'issues': routine_issues})

        except Exception as e:
            self.log_action(f"Error analyzing routines: {str(e)}")

    def log_action(self, message):
        with open(self.log_file_path, 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")

    def handle_new_feedback(self, event_data):
        self.analyze_logs_and_feedback()


def start_module(event_bus):
    """
    Entry point for the Automated Routine Checker module.
    """
    checker = AutomatedRoutineChecker()

    # Subscribe to feedback events
    event_bus.subscribe('new_user_feedback', checker.handle_new_feedback)

    # Initial analysis
    checker.analyze_logs_and_feedback()
