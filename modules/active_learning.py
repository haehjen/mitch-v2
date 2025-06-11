import os
import json
from datetime import datetime
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH

class ActiveLearning:
    def __init__(self):
        self.knowledge_base = {}
        self.load_knowledge()

    def load_knowledge(self):
        """Load existing knowledge from disk."""
        try:
            with open('/home/triad/mitch/data/knowledge.json', 'r') as f:
                self.knowledge_base = json.load(f)
        except FileNotFoundError:
            self.knowledge_base = {}

    def save_knowledge(self):
        """Save the updated knowledge base to disk."""
        with open('/home/triad/mitch/data/knowledge.json', 'w') as f:
            json.dump(self.knowledge_base, f)

    def log_action(self, action, data):
        """Log actions for auditing and inspection."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'data': data
            }
            log_file.write(json.dumps(log_entry) + '\n')

    def handle_feedback_event(self, event_data):
        """Process feedback to update the knowledge base."""
        self.log_action('feedback_received', event_data)
        feedback_type = event_data.get('type')
        feedback_content = event_data.get('content')

        if feedback_type and feedback_content:
            if feedback_type not in self.knowledge_base:
                self.knowledge_base[feedback_type] = []
            self.knowledge_base[feedback_type].append(feedback_content)
            self.save_knowledge()
            self.log_action('knowledge_updated', {
                'type': feedback_type,
                'content': feedback_content
            })

    def handle_interaction_event(self, event_data):
        """Learn from interactions by storing relevant context."""
        self.log_action('interaction_logged', event_data)
        interaction_context = event_data.get('context')

        if interaction_context:
            context_key = interaction_context.get('key')
            context_value = interaction_context.get('value')

            if context_key and context_value:
                if context_key not in self.knowledge_base:
                    self.knowledge_base[context_key] = []
                self.knowledge_base[context_key].append(context_value)
                self.save_knowledge()
                self.log_action('context_stored', {
                    'key': context_key,
                    'value': context_value
                })


def start_module(event_bus):
    active_learning = ActiveLearning()
    event_bus.subscribe('FEEDBACK_EVENT', active_learning.handle_feedback_event)
    event_bus.subscribe('INTERACTION_EVENT', active_learning.handle_interaction_event)
    
    print('Active Learning module started and listening for feedback and interaction events.')
