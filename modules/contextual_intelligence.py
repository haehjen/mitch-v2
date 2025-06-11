
import os
from core.event_bus import event_bus
import logging
import json

class ContextualIntelligence:
    def __init__(self):
        self.context_data = {}
        self.log_file_path = '/home/triad/mitch/logs/contextual_intelligence.log'
        self.load_context_data()
        
    def load_context_data(self):
        '''Loads context data from a persistent storage file.'''
        try:
            with open('/home/triad/mitch/data/context_data.json', 'r') as file:
                self.context_data = json.load(file)
        except FileNotFoundError:
            self.context_data = {}

    def save_context_data(self):
        '''Saves context data to a persistent storage file.'''
        with open('/home/triad/mitch/data/context_data.json', 'w') as file:
            json.dump(self.context_data, file)

    def log_action(self, message):
        '''Logs actions to a file.'''
        with open(self.log_file_path, 'a') as log_file:
            log_file.write(f"{message}\n")

    def analyze_event(self, event_data):
        '''Analyzes the event and updates context data accordingly.'''
        # Example analysis (this can be expanded based on more complex logic)
        event_type = event_data.get('type')
        if event_type:
            self.context_data['last_event_type'] = event_type
            self.log_action(f"Updated context with event type: {event_type}")
        self.save_context_data()

    def handle_interaction_event(self, event_data):
        '''Handles interaction events to update context.

        :param event_data: Data related to the interaction event.
        '''
        self.analyze_event(event_data)

    def handle_environment_change(self, event_data):
        '''Handles environment change events to update context.

        :param event_data: Data related to the environment change.
        '''
        self.analyze_event(event_data)

    def handle_system_status(self, event_data):
        '''Handles system status events to update context.

        :param event_data: Data related to the system status.
        '''
        self.analyze_event(event_data)

    def start(self):
        '''Starts the ContextualIntelligence module.'''
        event_bus.subscribe('interaction_event', self.handle_interaction_event)
        event_bus.subscribe('environment_change', self.handle_environment_change)
        event_bus.subscribe('system_status', self.handle_system_status)
        self.log_action("ContextualIntelligence module started.")


def start_module(event_bus):
    '''Entry point for the ContextualIntelligence module.'''
    contextual_intelligence = ContextualIntelligence()
    contextual_intelligence.start()
