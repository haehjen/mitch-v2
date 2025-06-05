import threading
import os
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
    "proxmon", "folder_access", "vision", "vision_ai"
}

shutdown_hooks = []
loaded_modules = []
thread_refs = []

def main():
    print("⚡ ECHO starting...")

    stream_mouth.start_stream_mouth()

    threading.Thread(target=peterjones.start_logger, daemon=True).start()
    threading.Thread(target=dispatcher.start_dispatcher, daemon=True).start()
    threading.Thread(target=interpreter.start_interpreter, daemon=True).start()
    threading.Thread(target=ears.start_ears, daemon=True).start()
    threading.Thread(target=visual_web.start_visual, daemon=True).start()
    threading.Thread(target=module_editor.start_module_editor, daemon=True).start()
    threading.Thread(target=transcriber.start_transcriber, daemon=True).start()

    if hasattr(ears, "shutdown"):
        shutdown_hooks.append(ears.shutdown)

    module_path = os.path.join(os.path.dirname(__file__), "modules")
    for filename in os.listdir(module_path):
        name, ext = os.path.splitext(filename)
        if ext != ".py" or name in EXCLUDED_MODULES:
            continue

        try:
            mod = importlib.import_module(f"modules.{name}")
            if hasattr(mod, "start_module"):
                threading.Thread(target=mod.start_module, args=(event_bus,), daemon=True).start()
                if DEBUG:
                    print(f"[AutoLoader] Started {name}.start_module()")
            elif hasattr(mod, "run"):
                threading.Thread(target=mod.run, args=(event_bus,), daemon=True).start()
                if DEBUG:
                    print(f"[AutoLoader] Started {name}.run()")
            else:
                if DEBUG:
                    print(f"[AutoLoader] {name}.py found but no usable entrypoint.")

            if hasattr(mod, "shutdown"):
                shutdown_hooks.append(mod.shutdown)
                loaded_modules.append(name)
        except Exception as e:
            if DEBUG:
                print(f"[AutoLoader] Failed to load {name}.py: {e}")

    echo_thought = EchoThoughtThread()
    echo_thought.start()
    shutdown_hooks.append(echo_thought.shutdown)  # ✅ Clean shutdown hook
    thread_refs.append(echo_thought)

    if DEBUG:
        print("🧠 Echo's self-evolution thread online.")

    print("✅ Echo V3 online. Awaiting input...")

    try:
        while True:
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
