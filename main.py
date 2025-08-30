import os
# --- Load secrets before anything else ---
from core.keys_loader import load_keys
load_keys()
import threading
import sys
import importlib
from core import peterjones, dispatcher
from core.event_bus import event_bus
from modules import (
    ears,
    interpreter,
    module_editor,
    transcriber,
    memory,
    stream_mouth,
    gpt_handler
)
from modules.visual import visual_web
from thought import EchoThoughtThread

DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"

EXCLUDED_MODULES = {
    "__init__", "ears", "interpreter", "module_editor", "dummy",
    "transcriber", "memory", "stream_mouth", "gpt_handler", "visual",
    "folder_access", "vision", "vision_ai"
}

shutdown_hooks = []
loaded_modules = []
thread_refs = []
_stop_event = threading.Event()

def _log_event(level: str, message: str, **kv):
    """Send a structured line into innermono.log via peterjones logger."""
    try:
        peterjones.log_event(level, message, kv)
    except Exception:
        # Fallback to print so we never lose signal
        print(f"[{level}] {message} | {kv}")

def _start_thread(target, name: str, *args, **kwargs):
    t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True, name=name)
    t.start()
    return t

def main():
    print("⚡ ECHO starting...")

    # Core subsystems
    stream_mouth.start_stream_mouth()
    _start_thread(peterjones.start_logger, "logger")
    _start_thread(dispatcher.start_dispatcher, "dispatcher")
    _start_thread(interpreter.start_interpreter, "interpreter")
    _start_thread(ears.start_ears, "ears")
    _start_thread(visual_web.start_visual, "visual_web")
    _start_thread(module_editor.start_module_editor, "module_editor")
    _start_thread(transcriber.start_transcriber, "transcriber")

    if hasattr(ears, "shutdown"):
        shutdown_hooks.append(ears.shutdown)

    # --- Explicitly ensure file_ingestor is online (so EMIT_FILE_READY is handled) ---
    try:
        from modules import file_ingestor  # noqa: F401
        if hasattr(file_ingestor, "start_module"):
            _start_thread(file_ingestor.start_module, "file_ingestor", event_bus)
            loaded_modules.append("file_ingestor")
            _log_event("INFO", "[boot] file_ingestor started")
        else:
            _log_event("WARNING", "[boot] file_ingestor has no start_module()")
    except Exception as e:
        _log_event("ERROR", "[boot] file_ingestor failed to start", error=str(e))

    # --- Autoload all other modules (with hard logging on failure) ---
    module_path = os.path.join(os.path.dirname(__file__), "modules")
    for filename in os.listdir(module_path):
        name, ext = os.path.splitext(filename)
        if ext != ".py" or name in EXCLUDED_MODULES or name == "file_ingestor":
            continue

        try:
            mod = importlib.import_module(f"modules.{name}")
            if hasattr(mod, "start_module"):
                _start_thread(mod.start_module, f"{name}.start_module", event_bus)
                if DEBUG:
                    print(f"[AutoLoader] Started {name}.start_module()")
                loaded_modules.append(name)
            elif hasattr(mod, "run"):
                _start_thread(mod.run, f"{name}.run", event_bus)
                if DEBUG:
                    print(f"[AutoLoader] Started {name}.run()")
                loaded_modules.append(name)
            else:
                if DEBUG:
                    print(f"[AutoLoader] {name}.py found but no usable entrypoint.")
                _log_event("INFO", "[autoload] module has no entrypoint", module=name)

            if hasattr(mod, "shutdown"):
                shutdown_hooks.append(mod.shutdown)

        except Exception as e:
            _log_event("ERROR", "[autoload] failed to load module", module=name, error=str(e))
            if DEBUG:
                print(f"[AutoLoader] Failed to load {name}.py: {e}")

    # Echo’s thought loop
    echo_thought = EchoThoughtThread()
    echo_thought.start()
    shutdown_hooks.append(echo_thought.shutdown)
    thread_refs.append(echo_thought)
    if DEBUG:
        print("🧠 Echo's self-evolution thread online.")

    print("✅ Echo V3 online. Awaiting input...")

    try:
        # Idle without burning CPU
        while not _stop_event.wait(1.0):
            pass
    except KeyboardInterrupt:
        print("\n🛑 MITCH shutdown signal received.")
        event_bus.emit("SHUTDOWN")

        for hook in shutdown_hooks:
            try:
                hook()
            except Exception as e:
                print(f"[Shutdown] Error in shutdown hook: {e}")

        for t in thread_refs:
            if t.is_alive():
                t.join(timeout=5)

        print(f"[Shutdown] Shutdown complete for modules: {', '.join(loaded_modules)}")

if __name__ == "__main__":
    main()
