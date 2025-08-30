from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
import json
import os

class CalendarManager:
    def __init__(self):
        self.calendar_file = '/home/triad/mitch/data/calendar.json'
        self.load_calendar()
        self.logger = get_logger("calendar_manager")

    def load_calendar(self):
        if os.path.exists(self.calendar_file):
            with open(self.calendar_file, 'r') as file:
                self.calendar = json.load(file)
        else:
            self.calendar = {}

    def save_calendar(self):
        with open(self.calendar_file, 'w') as file:
            json.dump(self.calendar, file)

    def create_event(self, event_data):
        event_id = len(self.calendar) + 1
        self.calendar[event_id] = event_data
        self.save_calendar()
        self.log_action(f"Event created: {event_data}")

    def update_event(self, event_id, event_data):
        if event_id in self.calendar:
            self.calendar[event_id] = event_data
            self.save_calendar()
            self.log_action(f"Event updated: {event_data}")
        else:
            self.log_action(f"Failed to update event: ID {event_id} not found.")

    def delete_event(self, event_id):
        if event_id in self.calendar:
            del self.calendar[event_id]
            self.save_calendar()
            self.log_action(f"Event deleted: ID {event_id}")
        else:
            self.log_action(f"Failed to delete event: ID {event_id} not found.")

    def log_action(self, message):
        self.logger.info(message)


def start_module(event_bus):
    manager = CalendarManager()

    def handle_create_event(data):
        manager.create_event(data)

    def handle_update_event(data):
        manager.update_event(data['id'], data['event'])

    def handle_delete_event(data):
        manager.delete_event(data['id'])

    event_bus.subscribe('CREATE_CALENDAR_EVENT', handle_create_event)
    event_bus.subscribe('UPDATE_CALENDAR_EVENT', handle_update_event)
    event_bus.subscribe('DELETE_CALENDAR_EVENT', handle_delete_event)

    IntentRegistry.register_intent(
        'create_calendar_event',
        handle_create_event,
        keywords=['create', 'new', 'calendar', 'event'],
        objects=[]
    )

    IntentRegistry.register_intent(
        'update_calendar_event',
        handle_update_event,
        keywords=['update', 'modify', 'change', 'calendar', 'event'],
        objects=[]
    )

    IntentRegistry.register_intent(
        'delete_calendar_event',
        handle_delete_event,
        keywords=['delete', 'remove', 'calendar', 'event'],
        objects=[]
    )
