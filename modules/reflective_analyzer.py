import json
import os
from core.event_bus import event_bus
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("reflective_analyzer")

LOG_FILE_PATH = os.path.join(MITCH_ROOT, "logs", "innermono.log")
INJECTION_PATH = f"{MITCH_ROOT}/data/injections/reflective_analysis.json"

class ReflectiveAnalyzer:
    def __init__(self):
        self.suggestions = []

    def analyze_logs(self):
        if not os.path.exists(LOG_FILE_PATH):
            return

        with open(LOG_FILE_PATH, 'r') as log_file:
            logs = log_file.readlines()

        # Simple analysis to find repetitive errors or warnings
        error_count = sum(1 for log in logs if '[ERROR]' in log)
        warning_count = sum(1 for log in logs if '[WARNING]' in log)

        if error_count > 0:
            self.suggestions.append(f"Consider investigating {error_count} errors logged recently.")
        if warning_count > 0:
            self.suggestions.append(f"Review {warning_count} warnings for potential improvements.")

        self.save_suggestions()

    def save_suggestions(self):
        suggestions_data = {
            "suggestions": self.suggestions,
            "timestamp": self._get_current_timestamp()
        }

        with open(INJECTION_PATH, 'w') as file:
            json.dump(suggestions_data, file)

        # Log the action
        logger.info(str(f"ReflectiveAnalyzer: Suggestions saved with {len(self.suggestions)} items.\n").rstrip("\n"))

    def _get_current_timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()


reflective_analyzer = ReflectiveAnalyzer()

def handle_inspection_event(data):
    # Trigger analysis when inspection digest is ready
    reflective_analyzer.analyze_logs()


def start_module(event_bus):
    event_bus.subscribe('inspection_digest_ready', handle_inspection_event)

    # Log module startup
    logger.info(str("ReflectiveAnalyzer module started.\n").rstrip("\n"))
