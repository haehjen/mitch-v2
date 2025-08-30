import asyncio
import threading
import time
import os
import json
from core.event_bus import event_bus

DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"

vision_ai = None

def get_vision_ai():
    global vision_ai
    if vision_ai is None:
        from modules.vision_ai import VisionAI
        vision_ai = VisionAI()
    return vision_ai

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
            description = asyncio.run(get_vision_ai().capture_and_describe())
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
            objects = asyncio.run(get_vision_ai().detect_objects())
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
        # Try to resolve via dynamic intents
        dynamic_path = "/home/triad/mitch/data/injections/dynamic_intents.json"
        intent_routed = False

        if os.path.exists(dynamic_path):
            try:
                with open(dynamic_path, "r") as f:
                    dynamic_data = json.load(f)
                    for entry in dynamic_data.get("intents", []):
                        if entry.get("intent") == intent:
                            action = entry.get("action")
                            if action:
                                routed_event = f"dynamic_intent:{action}"
                                event_bus.emit(routed_event, data)
                                event_bus.emit("EMIT_ACK", {
                                    "status": "dispatched",
                                    "intent": intent,
                                    "routed_event": routed_event
                                })
                                intent_routed = True
                                break
            except Exception as e:
                if DEBUG:
                    print(f"[DISPATCHER] Failed reading dynamic intents: {e}")

        if not intent_routed:
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
