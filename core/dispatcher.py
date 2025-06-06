import asyncio
import threading
import time
import os
from core.event_bus import event_bus
from modules.vision_ai import VisionAI

DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"

vision_ai = VisionAI()
_dispatcher_started = False

def handle_user_intent(data):
    if DEBUG:
        print("[DISPATCHER] handle_user_intent triggered")

    if not data:
        return

    intent = data.get("intent")
    params = data.get("params", {})
    token = str(time.time())

    if intent == "launch_drone":
        drone_ids = params.get("drone_ids", [])
        if DEBUG:
            print(f"[DISPATCHER] Launching drones: {', '.join(map(str, drone_ids))}")
        output = f"Launching drones {', '.join(map(str, drone_ids))}"
        event_bus.emit("EMIT_SPEAK", {
            "text": output,
            "source": "intent",
            "token": token
        })
        event_bus.emit("EMIT_ACK", {
            "status": "success",
            "intent": intent,
            "executed": f"{len(drone_ids)} drones"
        })
        event_bus.emit("EMIT_TOOL_RESULT", {
            "tool_call_id": data.get("tool_call_id"),
            "function_name": intent,
            "output": output
        })

    elif intent == "describe_scene":
        try:
            description = asyncio.run(vision_ai.capture_and_describe())
            event_bus.emit("EMIT_SPEAK", {
                "text": description,
                "source": "intent",
                "token": token
            })
            event_bus.emit("EMIT_TOOL_RESULT", {
                "tool_call_id": data.get("tool_call_id"),
                "function_name": intent,
                "output": description
            })
        except Exception as e:
            error_msg = f"Failed to describe the scene: {e}"
            event_bus.emit("EMIT_SPEAK", {
                "text": error_msg,
                "source": "intent",
                "token": token
            })
            event_bus.emit("EMIT_TOOL_RESULT", {
                "tool_call_id": data.get("tool_call_id"),
                "function_name": intent,
                "output": error_msg
            })

    elif intent == "detect_objects":
        try:
            objects = asyncio.run(vision_ai.detect_objects())
            event_bus.emit("EMIT_SPEAK", {
                "text": objects,
                "source": "intent",
                "token": token
            })
            event_bus.emit("EMIT_TOOL_RESULT", {
                "tool_call_id": data.get("tool_call_id"),
                "function_name": intent,
                "output": objects
            })
        except Exception as e:
            error_msg = f"Failed to detect objects: {e}"
            event_bus.emit("EMIT_SPEAK", {
                "text": error_msg,
                "source": "intent",
                "token": token
            })
            event_bus.emit("EMIT_TOOL_RESULT", {
                "tool_call_id": data.get("tool_call_id"),
                "function_name": intent,
                "output": error_msg
            })

    else:
        msg = f"Sorry, I didn't understand the command: {intent}"
        event_bus.emit("EMIT_SPEAK", {
            "text": msg,
            "source": "intent",
            "token": token
        })
        event_bus.emit("EMIT_FAILURE", {
            "intent": intent,
            "reason": "Unknown intent"
        })
        event_bus.emit("EMIT_TOOL_RESULT", {
            "tool_call_id": data.get("tool_call_id"),
            "function_name": intent,
            "output": msg
        })

def start_dispatcher():
    global _dispatcher_started
    if _dispatcher_started:
        if DEBUG:
            print(f"[DISPATCHER] Ignoring second call to start_dispatcher in thread {threading.current_thread().name}")
        return

    _dispatcher_started = True
    if DEBUG:
        print(f"[DISPATCHER] start_dispatcher() CALLED in thread {threading.current_thread().name}")

    event_bus.subscribe("EMIT_USER_INTENT", handle_user_intent)
    if DEBUG:
        print("[DISPATCHER] Subscribed to EMIT_USER_INTENT")
