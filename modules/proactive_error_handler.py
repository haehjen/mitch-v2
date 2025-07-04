import os
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/proactive_error_handler.log'
ERROR_LOG_FILE = '/home/triad/mitch/logs/error.log'

class ProactiveErrorHandler:
    def __init__(self):
        self.known_errors = {
            'Loop mic capture failed': 'This error indicates a microphone device issue. Try checking the device connection or driver.',
            'FileNotFoundError': 'A required file was not found. Please ensure all necessary files are in the correct location.'
        }

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def scan_for_errors(self):
        if not os.path.exists(ERROR_LOG_FILE):
            self.log_action('No error log file found. Skipping error scan.')
            return

        with open(ERROR_LOG_FILE, 'r') as error_log:
            for line in error_log.readlines():
                self.analyze_error(line)

    def analyze_error(self, log_line):
        for error_key in self.known_errors:
            if error_key in log_line:
                self.emit_error_notification(error_key, log_line)
                break

    def emit_error_notification(self, error_key, log_line):
        solution = self.known_errors[error_key]
        message = f'Error detected: {error_key}\nLog: {log_line}\nSuggested solution: {solution}'
        event_bus.emit('EMIT_SPEAK', {'message': message})
        self.log_action(f'Error notification emitted: {error_key}')

    def start_monitoring(self):
        self.log_action('Proactive error monitoring started.')
        self.scan_for_errors()


def start_module(event_bus):
    error_handler = ProactiveErrorHandler()
    error_handler.start_monitoring()
