import json
import threading
from datetime import datetime
from core.event_bus import event_bus

class UserBehaviorAnalyzer:
    def __init__(self):
        self.user_interactions = []
        self.running = True

    def log_interaction(self, interaction_data):
        """
        Log a user interaction.

        :param interaction_data: Dictionary containing interaction details
        """
        self.user_interactions.append({
            'timestamp': datetime.now().isoformat(),
            'interaction': interaction_data
        })
        self.log_action(f"Logged interaction: {interaction_data}")

    def analyze_behavior(self):
        """
        Analyze the logged user interactions to extract behavior patterns and trends.
        """
        # Example analysis: Count the frequency of specific interaction types
        interaction_counts = {}
        for entry in self.user_interactions:
            interaction_type = entry['interaction'].get('type', 'unknown')
            interaction_counts[interaction_type] = interaction_counts.get(interaction_type, 0) + 1

        # Log the analysis result
        analysis_result = {
            'total_interactions': len(self.user_interactions),
            'interaction_counts': interaction_counts
        }
        self.log_action(f"User behavior analysis: {json.dumps(analysis_result)}")

    def run(self):
        while self.running:
            self.analyze_behavior()
            time.sleep(3600)  # Run analysis every hour

    def stop(self):
        self.running = False

    def log_action(self, message):
        with open('/home/triad/mitch/logs/user_behavior_analyzer.log', 'a') as log_file:
            log_file.write(f"{datetime.now()} - {message}\n")

analyzer = UserBehaviorAnalyzer()

def start_module(event_bus):
    """
    Entry point for the User Behavior Analyzer module.
    """
    def handle_user_interaction(event_data):
        analyzer.log_interaction(event_data)

    event_bus.subscribe('user_interaction', handle_user_interaction)
    analyzer_thread = threading.Thread(target=analyzer.run)
    analyzer_thread.start()