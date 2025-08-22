import os
import json
from datetime import datetime
from core.event_bus import event_bus

class UserFeedbackAnalyzer:
    def __init__(self):
        self.feedback_file = '/home/triad/mitch/logs/user_feedback.json'
        self.analysis_log = '/home/triad/mitch/logs/user_feedback_analysis.log'

    def load_feedback(self):
        if os.path.exists(self.feedback_file):
            with open(self.feedback_file, 'r') as file:
                return json.load(file)
        return []

    def analyze_feedback(self, feedback_data):
        analysis_results = {
            'total_feedback': len(feedback_data),
            'positive_feedback': 0,
            'negative_feedback': 0,
            'common_issues': {},
            'feature_requests': {}
        }

        for feedback in feedback_data:
            sentiment = feedback.get('sentiment')
            if sentiment == 'positive':
                analysis_results['positive_feedback'] += 1
            elif sentiment == 'negative':
                analysis_results['negative_feedback'] += 1

            issues = feedback.get('issues', [])
            for issue in issues:
                analysis_results['common_issues'][issue] = analysis_results['common_issues'].get(issue, 0) + 1

            requests = feedback.get('feature_requests', [])
            for request in requests:
                analysis_results['feature_requests'][request] = analysis_results['feature_requests'].get(request, 0) + 1

        self.log_analysis(analysis_results)

    def log_analysis(self, analysis_results):
        log_entry = f"{datetime.now()} - Analysis Results: {json.dumps(analysis_results)}\n"
        with open(self.analysis_log, 'a') as log_file:
            log_file.write(log_entry)

    def handle_new_feedback(self, event_data):
        feedback_data = self.load_feedback()
        feedback_data.append(event_data)
        with open(self.feedback_file, 'w') as file:
            json.dump(feedback_data, file, indent=2)
        self.analyze_feedback(feedback_data)

user_feedback_analyzer = UserFeedbackAnalyzer()

def start_module(event_bus):
    """
    Entry point for the User Feedback Analyzer module.
    """
    event_bus.subscribe('new_user_feedback', user_feedback_analyzer.handle_new_feedback)
