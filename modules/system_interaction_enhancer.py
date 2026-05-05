import os
import json
from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("system_interaction_enhancer")

LOG_FILE = os.path.join(MITCH_ROOT, "logs", "innermono.log")
INJECTIONS_DIR = f"{MITCH_ROOT}/data/injections/"

class FileManager:
    @staticmethod
    def list_directory(path):
        try:
            files = os.listdir(path)
            return {'status': 'success', 'files': files}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def create_file(path, filename):
        try:
            with open(os.path.join(path, filename), 'w') as f:
                f.write('')
            return {'status': 'success', 'message': f'File {filename} created.'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def delete_file(path, filename):
        try:
            os.remove(os.path.join(path, filename))
            return {'status': 'success', 'message': f'File {filename} deleted.'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

file_manager = FileManager()

def handle_list_directory_event(data):
    path = data.get('path', '/')
    result = file_manager.list_directory(path)
    log_action(f"Listed directory {path}: {result}")
    save_context_change('list_directory', result)


def handle_create_file_event(data):
    path = data.get('path', '/')
    filename = data.get('filename', 'new_file.txt')
    result = file_manager.create_file(path, filename)
    log_action(f"Created file {filename} in {path}: {result}")
    save_context_change('create_file', result)


def handle_delete_file_event(data):
    path = data.get('path', '/')
    filename = data.get('filename', '')
    result = file_manager.delete_file(path, filename)
    log_action(f"Deleted file {filename} in {path}: {result}")
    save_context_change('delete_file', result)


def log_action(message):
    logger.info(str(f"{message}\n").rstrip("\n"))


def save_context_change(action, data):
    context = {'action': action, 'result': data}
    with open(os.path.join(INJECTIONS_DIR, f'{action}_context.json'), 'w') as file:
        json.dump(context, file)


def start_module(event_bus):
    event_bus.subscribe('LIST_DIRECTORY', handle_list_directory_event)
    event_bus.subscribe('CREATE_FILE', handle_create_file_event)
    event_bus.subscribe('DELETE_FILE', handle_delete_file_event)

    IntentRegistry.register_intent(
        'list_files',
        handle_list_directory_event,
        keywords=['list', 'files', 'show', 'directory'],
        objects=[]
    )

    IntentRegistry.register_intent(
        'create_file',
        handle_create_file_event,
        keywords=['create', 'file', 'new', 'document'],
        objects=[]
    )

    IntentRegistry.register_intent(
        'delete_file',
        handle_delete_file_event,
        keywords=['delete', 'remove', 'file', 'erase'],
        objects=[]
    )

    log_action("System Interaction Enhancer module started.")
