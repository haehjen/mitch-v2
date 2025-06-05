import speech_recognition as sr
import time
import os
from core.event_bus import event_bus

DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

recent_files = set()
recent_phrases = {}
mute = False
running = True  # ✅ Used for clean shutdown

def handle_mute(_):
    global mute
    mute = True
    if DEBUG:
        print("[Transcriber] Muted.")

def handle_unmute(_):
    global mute
    mute = False
    if DEBUG:
        print("[Transcriber] Unmuted.")

def handle_audio_captured(data):
    global recent_files, recent_phrases, mute, running
    if not running:
        return

    path = data.get("path")
    if not path:
        if DEBUG:
            print("[Transcriber] No audio path provided")
        return

    if mute:
        if DEBUG:
            print("[Transcriber] Ignored due to mute state.")
        return

    if path in recent_files:
        if DEBUG:
            print("[Transcriber] Ignoring duplicate file:", path)
        return

    if not os.path.exists(path):
        if DEBUG:
            print(f"[Transcriber] File missing: {path}")
        return
    if os.path.getsize(path) < 1024:
        if DEBUG:
            print(f"[Transcriber] File too small to process: {path}")
        return

    time.sleep(0.1)
    recent_files.add(path)

    if DEBUG:
        print(f"[Transcriber] Processing audio from {path}")

    try:
        with sr.AudioFile(path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            text_lower = text.strip().lower()

            now = time.time()
            last_time = recent_phrases.get(text_lower, 0)

            if now - last_time < 2:
                if DEBUG:
                    print(f"[Transcriber] Ignoring duplicate phrase: {text}")
                return

            recent_phrases[text_lower] = now
            if DEBUG:
                print(f"[Transcriber] Recognized: {text}")
            event_bus.emit("EMIT_INPUT_RECEIVED", {"text": text, "source": "user"})

    except sr.UnknownValueError:
        if DEBUG:
            print("[Transcriber] Could not understand the audio")
    except sr.RequestError as e:
        if DEBUG:
            print(f"[Transcriber] Speech recognition service error: {e}")
    except Exception as e:
        if DEBUG:
            print(f"[Transcriber] Failed to process audio: {e}")

def start_transcriber():
    if DEBUG:
        print("[Transcriber] Online and listening for EMIT_AUDIO_CAPTURED...")

    event_bus.subscribe("EMIT_AUDIO_CAPTURED", handle_audio_captured)
    event_bus.subscribe("MUTE_EARS", handle_mute)
    event_bus.subscribe("UNMUTE_EARS", handle_unmute)

def shutdown():
    global running
    running = False
    if DEBUG:
        print("[Transcriber] Shutdown initiated.")
