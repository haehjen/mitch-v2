import json
from core.event_bus import event_bus

class UserProfileManager:
    def __init__(self):
        self.user_profiles = self.load_user_profiles()

    def load_user_profiles(self):
        try:
            with open('/home/triad/mitch/data/user_profiles.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_user_profiles(self):
        with open('/home/triad/mitch/data/user_profiles.json', 'w') as file:
            json.dump(self.user_profiles, file)

    def update_user_profile(self, user_id, data):
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {}
        self.user_profiles[user_id].update(data)
        self.save_user_profiles()
        self.log_action(f"Updated profile for user {user_id}.")

    def get_user_profile(self, user_id):
        return self.user_profiles.get(user_id, {})

    def log_action(self, message):
        with open('/home/triad/mitch/logs/user_personalization_manager.log', 'a') as log_file:
            log_file.write(f"{message}\n")

user_profile_manager = UserProfileManager()

def handle_user_interaction(event_data):
    user_id = event_data.get('user_id')
    interaction_data = event_data.get('interaction_data')
    if user_id and interaction_data:
        user_profile_manager.update_user_profile(user_id, interaction_data)

def start_module(event_bus):
    """
    Entry point for the User Personalization Manager module.
    """
    event_bus.subscribe('user_interaction', handle_user_interaction)
    user_profile_manager.log_action("User Personalization Manager module started.")
