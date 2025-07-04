import os
import json
from datetime import datetime, timedelta
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/focus_session_manager.log'

class FocusSessionManager:
    def __init__(self):
        self.sessions = []
        self.load_sessions()

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def load_sessions(self):
        try:
            with open('/home/triad/mitch/data/focus_sessions.json', 'r') as file:
                self.sessions = json.load(file)
                self.log_action('Sessions loaded successfully.')
        except FileNotFoundError:
            self.sessions = []
            self.log_action('No existing session file found, starting fresh.')

    def save_sessions(self):
        with open('/home/triad/mitch/data/focus_sessions.json', 'w') as file:
            json.dump(self.sessions, file)
            self.log_action('Sessions saved successfully.')

    def start_focus_session(self, session_data):
        session_data['start_time'] = datetime.now().isoformat()
        self.sessions.append(session_data)
        self.save_sessions()
        self.log_action(f'Started focus session: {session_data}')
        # Emit an event to notify that a focus session has started
        event_bus.emit('FOCUS_SESSION_STARTED', {'session': session_data})

    def end_focus_session(self, session_id):
        for session in self.sessions:
            if session['id'] == session_id:
                session['end_time'] = datetime.now().isoformat()
                self.save_sessions()
                self.log_action(f'Ended focus session: {session}')
                # Emit an event to notify that a focus session has ended
                event_bus.emit('FOCUS_SESSION_ENDED', {'session': session})
                return
        self.log_action(f'Focus session not found: {session_id}')

    def list_focus_sessions(self):
        return self.sessions

    def handle_start_focus_session(self, event_data):
        self.start_focus_session(event_data)

    def handle_end_focus_session(self, event_data):
        self.end_focus_session(event_data['id'])


def start_module(event_bus):
    manager = FocusSessionManager()
    event_bus.subscribe('START_FOCUS_SESSION', manager.handle_start_focus_session)
    event_bus.subscribe('END_FOCUS_SESSION', manager.handle_end_focus_session)
    # Log the module start
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f'Module started at {datetime.now().isoformat()}\n')
