from core.event_bus import event_bus
import datetime
import json

class UserContextualInsight:
    def __init__(self):
        self.interaction_logs = []

    def log_interaction(self, interaction):
        timestamp = datetime.datetime.now()
        self.interaction_logs.append({"timestamp": timestamp, "interaction": interaction})
        self._save_log_entry(interaction, timestamp)

    def _save_log_entry(self, interaction, timestamp):
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "interaction": interaction
        }
        with open('/home/triad/mitch/logs/user_contextual_insight.log', 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')

    def analyze_interactions(self):
        # Simple analysis to identify trends or patterns
        interaction_count = len(self.interaction_logs)
        if interaction_count == 0:
            return

        # Example analysis: find peak interaction times
        peak_times = self._find_peak_interaction_times()
        insights = {
            "total_interactions": interaction_count,
            "peak_interaction_times": peak_times
        }
        self._emit_insights(insights)

    def _find_peak_interaction_times(self):
        # A basic method to find times with the most interactions
        hour_groups = {}
        for entry in self.interaction_logs:
            hour = entry["timestamp"].hour
            if hour not in hour_groups:
                hour_groups[hour] = 0
            hour_groups[hour] += 1

        peak_hour = max(hour_groups, key=hour_groups.get)
        return peak_hour

    def _emit_insights(self, insights):
        event_bus.emit('user_contextual_insights', insights)

    def handle_user_interaction(self, event_data):
        interaction = event_data.get('prompt', '')
        self.log_interaction(interaction)
        self.analyze_interactions()

    def start(self):
        event_bus.subscribe('user_interaction', self.handle_user_interaction)


def start_module(event_bus):
    """
    Entry point for the User Contextual Insight module.
    """
    insight_module = UserContextualInsight()
    insight_module.start()
