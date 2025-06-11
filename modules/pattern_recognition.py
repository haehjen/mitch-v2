import os
import json
from collections import defaultdict
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class PatternRecognition:
    def __init__(self):
        self.event_patterns = defaultdict(list)

    def log_event(self, event_data):
        """Log the event data for pattern analysis."""
        event_type = event_data.get('event_type')
        timestamp = event_data.get('timestamp')
        self.event_patterns[event_type].append(timestamp)
        self._write_log({
            'event_type': event_type,
            'timestamp': timestamp
        })

    def _write_log(self, data):
        """Write the event data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def analyze_patterns(self):
        """Analyze logged events to find patterns."""
        pattern_summary = {}
        for event_type, timestamps in self.event_patterns.items():
            if len(timestamps) > 1:
                intervals = [t2 - t1 for t1, t2 in zip(timestamps[:-1], timestamps[1:])]
                average_interval = sum(intervals) / len(intervals)
                pattern_summary[event_type] = average_interval
        return pattern_summary

    def handle_event(self, event_data):
        """Handle events emitted by other modules."""
        self.log_event(event_data)
        pattern_summary = self.analyze_patterns()
        if pattern_summary:
            event_bus.emit('PATTERN_RECOGNIZED', pattern_summary)


def start_module(event_bus):
    pattern_recognition = PatternRecognition()
    event_bus.subscribe('EMIT_AUDIO_CAPTURED', pattern_recognition.handle_event)
    event_bus.subscribe('EMIT_SPEAK_END', pattern_recognition.handle_event)
    
    print('Pattern Recognition module started and listening for events.')
