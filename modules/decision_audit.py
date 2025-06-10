import os
import json
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/decision_audit.log'

class DecisionAudit:
    def __init__(self):
        self.decisions = []

    def log_decision(self, decision_data):
        """Log the decision details and outcome."""
        timestamp = datetime.now().isoformat()
        decision_entry = {
            'timestamp': timestamp,
            'decision': decision_data.get('decision'),
            'outcome': decision_data.get('outcome')
        }
        self.decisions.append(decision_entry)
        self._write_log(decision_entry)

    def _write_log(self, data):
        """Write the decision data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def analyze_decisions(self):
        """Analyze logged decisions to identify patterns and outcomes."""
        analysis = {}
        for entry in self.decisions:
            decision = entry['decision']
            outcome = entry['outcome']
            if decision not in analysis:
                analysis[decision] = {'success': 0, 'failure': 0}
            if outcome == 'success':
                analysis[decision]['success'] += 1
            else:
                analysis[decision]['failure'] += 1
        return analysis

    def handle_decision_event(self, event_data):
        """Handle decision events emitted by other modules."""
        self.log_decision(event_data)


def start_module(event_bus):
    decision_audit = DecisionAudit()
    event_bus.subscribe('EMIT_DECISION_EVENT', decision_audit.handle_decision_event)
    
    print('Decision Audit module started and listening for decision events.')
