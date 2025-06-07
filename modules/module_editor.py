import os
from pathlib import Path
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

logger = get_logger("module_editor")

# Utility to verify the path stays inside MITCH_ROOT
def safe_path(filename):
    base = Path(MITCH_ROOT).resolve()
    abs_path = Path(filename).resolve()
    if abs_path.is_relative_to(base):
        return str(abs_path)
    raise ValueError(f"Access denied: {abs_path} is outside {base}")

def handle_module_create(data):
    filename = data.get("filename")
    code = data.get("code")
    if not filename or not code:
        logger.warning("Missing filename or code.")
        return

    try:
        path = safe_path(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if os.path.exists(path):
            logger.warning(f"File already exists: {path}")
            return

        with open(path, "w") as f:
            f.write(code)
        logger.info(f"Created module: {path}")
    except Exception as e:
        logger.error(f"Create failed: {e}")

def handle_module_read(data):
    filename = data.get("filename")
    if not filename:
        logger.warning("Missing filename for read.")
        return

    try:
        path = safe_path(filename)
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}")
            return

        with open(path, "r") as f:
            content = f.read()

        event_bus.emit("EMIT_MODULE_CONTENT", {
            "filename": filename,
            "content": content
        })
        logger.info(f"Read module: {path}")
    except Exception as e:
        logger.error(f"Read failed: {e}")

def handle_module_edit(data):
    filename = data.get("filename")
    new_content = data.get("content")
    if not filename or not new_content:
        logger.warning("Missing filename or new content for edit.")
        return

    try:
        path = safe_path(filename)
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}")
            return

        backup_path = path + ".bak"
        os.rename(path, backup_path)

        with open(path, "w") as f:
            f.write(new_content)

        logger.info(f"Edited module: {path} (backup at {backup_path})")
    except Exception as e:
        logger.error(f"Edit failed: {e}")

def handle_main_append(data):
    line = data.get("line", "").strip()
    if not line:
        logger.warning("No line provided to append to main.py")
        return

    try:
        main_path = os.path.join(MITCH_ROOT, "main.py")
        if not os.path.exists(main_path):
            logger.warning("main.py not found.")
            return

        with open(main_path, "a") as f:
            f.write(f"\n{line}")

        logger.info(f"Appended to main.py: {line}")
    except Exception as e:
        logger.error(f"Failed to append to main.py: {e}")

def start_module_editor():
    logger.info(f"Online and enforcing sandbox to {MITCH_ROOT}")
    event_bus.subscribe("EMIT_MODULE_CREATE", handle_module_create)
    event_bus.subscribe("EMIT_MODULE_READ", handle_module_read)
    event_bus.subscribe("EMIT_MODULE_EDIT", handle_module_edit)
    event_bus.subscribe("EMIT_APPEND_TO_MAIN", handle_main_append)
