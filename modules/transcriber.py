import speech_recognition as sr
import time
import os
from core.event_bus import event_bus
from core.peterjones import get_logger
from core.config import DEBUG

logger = get_logger("transcriber")

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

recent_files = set()
recent_phrases = {}
mute = False
running = True

MAX_RECENT = 100  # Maximum tracked recent files/phrases

# Global debug mode (override if needed)
DEBUG = os.getenv("DEBUG", "false").lower() in ["1", "true", "yes"]

def handle_mute(_):
    global mute
    mute = True
    if DEBUG:
        logger.debug("Muted.")

def handle_unmute(_):
    global mute
    mute = False
    if DEBUG:
        logger.debug("Unmuted.")

def _trim_recent():
    global recent_phrases, recent_files
    now = time.time()
    for phrase in list(recent_phrases.keys()):
        if now - recent_phrases[phrase] > 60:
            del recent_phrases[phrase]
    while len(recent_files) > MAX_RECENT:
        recent_files.pop()

def _cleanup(path):
    try:
        os.remove(path)
        if DEBUG:
            logger.debug(f"Deleted temp audio: {path}")
    except Exception as e:
        logger.warning(f"Failed to delete temp audio: {path} | {e}")

def handle_audio_captured(data):
    global recent_files, recent_phrases, mute, running
    if not running:
        return

    path = data.get("path")
    if not path:
        if DEBUG:
            logger.warning("No audio path provided")
        return

    if mute:
        if DEBUG:
            logger.debug("Ignored due to mute state.")
        return

    if path in recent_files:
        if DEBUG:
            logger.debug(f"Ignoring duplicate file: {path}")
        return

    if not os.path.exists(path):
        if DEBUG:
            logger.warning(f"File missing: {path}")
        return

    if os.path.getsize(path) < 1024:
        if DEBUG:
            logger.debug(f"File too small to process: {path}")
        _cleanup(path)
        return

    time.sleep(0.1)
    recent_files.add(path)
    _trim_recent()

    if DEBUG:
        logger.debug(f"Processing audio from {path}")

    try:
        with sr.AudioFile(path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            text_lower = text.strip().lower()

            now = time.time()
            last_time = recent_phrases.get(text_lower, 0)

            if now - last_time < 2:
                if DEBUG:
                    logger.debug(f"Ignoring duplicate phrase: {text}")
                _cleanup(path)
                return

            recent_phrases[text_lower] = now
            logger.info(f"Recognized: {text}")
            event_bus.emit("EMIT_INPUT_RECEIVED", {"text": text, "source": "user"})
            _cleanup(path)

    except sr.UnknownValueError:
        if DEBUG:
            logger.debug("Could not understand the audio")
        event_bus.emit("EMIT_TRANSCRIBE_FAILED", {"path": path, "reason": "unintelligible"})
        _cleanup(path)

    except sr.RequestError as e:
        if DEBUG:
            logger.warning(f"Speech recognition service error: {e}")
        event_bus.emit("EMIT_TRANSCRIBE_FAILED", {"path": path, "reason": str(e)})
        _cleanup(path)

    except Exception as e:
        if DEBUG:
            logger.error(f"Failed to process audio: {e}")
        event_bus.emit("EMIT_TRANSCRIBE_FAILED", {"path": path, "reason": str(e)})
        _cleanup(path)

def start_transcriber():
    logger.info("Transcriber online and listening for EMIT_AUDIO_CAPTURED...")
    event_bus.subscribe("EMIT_AUDIO_CAPTURED", handle_audio_captured)
    event_bus.subscribe("MUTE_EARS", handle_mute)
    event_bus.subscribe("UNMUTE_EARS", handle_unmute)

def shutdown():
    global running
    running = False
    logger.info("Shutdown initiated.")
