import logging
import os
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EventLogger:
    def __init__(self):
        self.log_path = log_path

    def log_event(self, event_data):
        try:
            event_name = event_data.get('event_name', 'unknown_event')
            event_details = event_data.get('details', {})
            logging.info(f"Event: {event_name} | Details: {event_details}")
        except Exception as e:
            logging.error(f"Failed to log event: {e}")

    def save_context_change(self, context_data):
        try:
            injections_dir = "/home/triad/mitch/data/injections/"
            os.makedirs(injections_dir, exist_ok=True)
            output_path = os.path.join(injections_dir, "event_context_change.json")
            with open(output_path, "w") as file:
                json.dump(context_data, file)
            logging.info("Context change saved for event.")
        except Exception as e:
            logging.error(f"Failed to save context change: {e}")


def start_module(event_bus):
    logger = EventLogger()

    event_names = [
        'EMIT_SPEAK', 'EMIT_CHAT_REQUEST', 'EMIT_MODULE_REQUEST',
        'EMIT_TOOL_RESULT', 'EMIT_SPEAK_CHUNK', 'EMIT_SPEAK_END',
        'EMIT_VISUAL_TOKEN', 'EMIT_VIDEO_FEED', 'EMIT_TOKEN_REGISTERED',
        'module_feedback', 'EMIT_USER_INTENT', 'EMIT_INPUT_RECEIVED',
        'HOUSECORE_INPUT', 'EMIT_MODULE_CREATE', 'EMIT_AUDIO_CAPTURED',
        'EMIT_MODULE_READ', 'MUTE_EARS', 'restart_vm', 'get_vm_status',
        'UNMUTE_EARS', 'EMIT_MODULE_EDIT', 'EMIT_APPEND_TO_MAIN',
        'system_update', 'user_feedback', 'EMIT_PUBLISH_DIGEST',
        'EMIT_TRANSCRIBE_FAILED', 'SHUTDOWN', 'inspection_digest_ready',
        'ECHO_HEARTBEAT', 'check_system_health', 'system_health_status',
        'user_interaction'
    ]

    for event_name in event_names:
        event_bus.subscribe(event_name, logger.log_event)

    logging.info("Event Logger module started and listening for system events.")
