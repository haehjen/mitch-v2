import os
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/audio_diagnostics.log'

class AudioDiagnostics:
    def __init__(self):
        self.error_count = 0

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def handle_audio_error(self, event_data):
        self.error_count += 1
        self.log_action(f"Audio error detected: {event_data['error_message']}")
        if self.error_count > 5:  # Example threshold
            self.emit_warning()

    def emit_warning(self):
        warning_message = "Multiple audio errors detected. Please check your audio input devices."
        event_bus.emit('EMIT_SPEAK', {'message': warning_message})
        self.log_action('Warning emitted to user due to repeated audio errors.')
        self.error_count = 0  # Reset count after warning


def start_module(event_bus):
    diagnostics = AudioDiagnostics()
    event_bus.subscribe('AUDIO_CAPTURE_ERROR', diagnostics.handle_audio_error)

    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
