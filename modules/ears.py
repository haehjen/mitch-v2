import sounddevice as sd
import soundfile as sf
import threading
import time
import tempfile
import os
from core.event_bus import event_bus
from core.peterjones import get_logger

DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"
logger = get_logger("ears")

is_speaking = False  # Flag to pause listening while speaking
WEBCAM_MIC_INDEX = 1  # Based on sounddevice index scan
stop_event = threading.Event()  # Used to cleanly shut down threads

def on_speak_end(_):
    global is_speaking
    is_speaking = False

def pause_microphone_briefly(_):
    global is_speaking
    is_speaking = True
    if DEBUG:
        logger.debug("Detected EMIT_INPUT_RECEIVED, pausing mic for 3s to test TTS contention...")
    time.sleep(3)
    is_speaking = False

def continuous_microphone_listener():
    global is_speaking
    samplerate = 44100
    duration = 5

    while not stop_event.is_set():
        if is_speaking:
            time.sleep(0.2)
            continue

        try:
            if DEBUG:
                logger.debug("Listening continuously from webcam mic...")

            audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16', device=WEBCAM_MIC_INDEX)
            sd.wait()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir="/tmp") as temp_file:
                wav_path = temp_file.name
                sf.write(wav_path, audio, samplerate)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Ensure file is fully written to disk

            if DEBUG:
                logger.debug(f"Captured loop sample to {wav_path}")

            event_bus.emit("EMIT_AUDIO_CAPTURED", {"path": wav_path})

        except Exception as e:
            logger.error(f"Loop mic capture failed: {e}")
            time.sleep(1)

def listen_keyboard():
    while not stop_event.is_set():
        try:
            text = input("⌨️  [Text Mode] Type your command below:\n>>> ").strip()
            if text:
                event_bus.emit("EMIT_INPUT_RECEIVED", {"text": text, "source": "user"})
        except EOFError:
            break

def start_keyboard():
    threading.Thread(target=listen_keyboard, daemon=True).start()

def start_microphone():
    threading.Thread(target=continuous_microphone_listener, daemon=True).start()

def start_ears():
    if DEBUG:
        logger.debug("start_ears() initializing listener threads...")
    event_bus.subscribe("EMIT_SPEAK_END", on_speak_end)
    event_bus.subscribe("EMIT_INPUT_RECEIVED", pause_microphone_briefly)
    start_microphone()
    start_keyboard()

def shutdown():
    stop_event.set()
    logger.info("Shutdown signal received. Terminating listener loops.")
