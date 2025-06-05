import os
from core.event_bus import event_bus
from core.config import MITCH_ROOT

# Utility to verify the path stays inside MITCH_ROOT
def safe_path(filename):
    abs_path = os.path.abspath(filename)
    if abs_path.startswith(MITCH_ROOT):
        return abs_path
    raise ValueError(f"Access denied: {abs_path} is outside MITCH root")

def handle_module_create(data):
    filename = data.get("filename")
    code = data.get("code")
    if not filename or not code:
        print("[ModuleEditor] Missing filename or code.")
        return

    try:
        path = safe_path(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if os.path.exists(path):
            print(f"[ModuleEditor] File already exists: {path}")
            return

        with open(path, "w") as f:
            f.write(code)
        print(f"[ModuleEditor] Created module: {path}")
    except Exception as e:
        print(f"[ModuleEditor] Create failed: {e}")

def handle_module_read(data):
    filename = data.get("filename")
    if not filename:
        print("[ModuleEditor] Missing filename for read.")
        return

    try:
        path = safe_path(filename)
        if not os.path.exists(path):
            print(f"[ModuleEditor] File not found: {path}")
            return

        with open(path, "r") as f:
            content = f.read()

        event_bus.emit("EMIT_MODULE_CONTENT", {
            "filename": filename,
            "content": content
        })
        print(f"[ModuleEditor] Read module: {path}")
    except Exception as e:
        print(f"[ModuleEditor] Read failed: {e}")

def handle_module_edit(data):
    filename = data.get("filename")
    new_content = data.get("content")
    if not filename or not new_content:
        print("[ModuleEditor] Missing filename or new content for edit.")
        return

    try:
        path = safe_path(filename)
        if not os.path.exists(path):
            print(f"[ModuleEditor] File not found: {path}")
            return

        backup_path = path + ".bak"
        os.rename(path, backup_path)

        with open(path, "w") as f:
            f.write(new_content)

        print(f"[ModuleEditor] Edited module: {path} (backup at {backup_path})")
    except Exception as e:
        print(f"[ModuleEditor] Edit failed: {e}")

def handle_main_append(data):
    line = data.get("line", "").strip()
    if not line:
        print("[ModuleEditor] No line provided to append to main.py")
        return

    try:
        main_path = os.path.join(MITCH_ROOT, "main.py")
        if not os.path.exists(main_path):
            print("[ModuleEditor] main.py not found.")
            return

        with open(main_path, "a") as f:
            f.write(f"\n{line}")

        print(f"[ModuleEditor] Appended to main.py: {line}")
    except Exception as e:
        print(f"[ModuleEditor] Failed to append to main.py: {e}")

def start_module_editor():
    print(f"[ModuleEditor] Online and enforcing sandbox to {MITCH_ROOT}")
    event_bus.subscribe("EMIT_MODULE_CREATE", handle_module_create)
    event_bus.subscribe("EMIT_MODULE_READ", handle_module_read)
    event_bus.subscribe("EMIT_MODULE_EDIT", handle_module_edit)
    event_bus.subscribe("EMIT_APPEND_TO_MAIN", handle_main_append)
