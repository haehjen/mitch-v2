import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/automatic_log_analyzer.log'

class AutomaticLogAnalyzer:
    def __init__(self):
        self.logs_dir = '/home/triad/mitch/logs/'
        self.inspection_digest_path = '/home/triad/mitch/logs/inspection_digest.json'
        self.analysis_interval = 60 * 60  # Analyze logs every hour

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def analyze_logs(self):
        self.log_action('Starting log analysis.')
        insights = {}
        for log_file in os.listdir(self.logs_dir):
            if log_file.endswith('.log'):
                file_path = os.path.join(self.logs_dir, log_file)
                with open(file_path, 'r') as file:
                    content = file.readlines()
                    insights[log_file] = self.extract_insights(content)
        self.save_inspection_digest(insights)
        self.log_action('Log analysis completed and insights saved.')

    def extract_insights(self, log_lines):
        error_count = sum(1 for line in log_lines if 'ERROR' in line)
        warning_count = sum(1 for line in log_lines if 'WARNING' in line)
        recommendations = []

        if error_count > 5:
            recommendations.append('Consider reviewing frequent errors.')
        if warning_count > 10:
            recommendations.append('Check warning messages for potential issues.')

        return {
            'error_count': error_count,
            'warning_count': warning_count,
            'recommendations': recommendations
        }

    def save_inspection_digest(self, insights):
        with open(self.inspection_digest_path, 'w') as digest_file:
            json.dump(insights, digest_file)

    def start_analysis_loop(self):
        self.log_action('Automatic log analyzer started.')
        while True:
            self.analyze_logs()
            sleep(self.analysis_interval)


def start_module(event_bus):
    log_analyzer = AutomaticLogAnalyzer()
    Thread(target=log_analyzer.start_analysis_loop, daemon=True).start()

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
