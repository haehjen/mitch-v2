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
MIC_ENABLED = os.getenv("MITCH_ENABLE_MIC", "true").lower() == "true"
WEBCAM_MIC_INDEX = int(os.getenv("MITCH_WEBCAM_MIC_INDEX", "1"))
SAMPLERATE = int(os.getenv("MITCH_MIC_SAMPLERATE", "44100"))
CAPTURE_DURATION = int(os.getenv("MITCH_MIC_CAPTURE_SECONDS", "10"))
ERROR_LOG_INTERVAL = float(os.getenv("MITCH_MIC_ERROR_LOG_INTERVAL", "30"))
stop_event = threading.Event()  # Used to cleanly shut down threads
_pause_until = 0.0
_last_error_log = 0.0

def on_speak_end(_):
    global is_speaking
    is_speaking = False

def pause_microphone_briefly(_):
    global is_speaking, _pause_until
    is_speaking = True
    _pause_until = max(_pause_until, time.time() + 3.0)
    if DEBUG:
        logger.debug("Detected EMIT_INPUT_RECEIVED, pausing mic for 3s.")


def _mic_device_available(index: int) -> bool:
    try:
        devices = sd.query_devices()
        if index < 0 or index >= len(devices):
            return False
        return int(devices[index].get("max_input_channels", 0)) > 0
    except Exception:
        return False

def continuous_microphone_listener():
    global is_speaking, _last_error_log

    while not stop_event.is_set():
        now = time.time()
        if _pause_until > now:
            time.sleep(0.2)
            continue
        if is_speaking:
            is_speaking = False

        if not _mic_device_available(WEBCAM_MIC_INDEX):
            if now - _last_error_log >= ERROR_LOG_INTERVAL:
                logger.warning(
                    f"Mic device index {WEBCAM_MIC_INDEX} unavailable; retrying."
                )
                _last_error_log = now
            time.sleep(2)
            continue

        try:
            if DEBUG:
                logger.debug("Listening continuously from webcam mic...")

            audio = sd.rec(
                int(CAPTURE_DURATION * SAMPLERATE),
                samplerate=SAMPLERATE,
                channels=1,
                dtype="int16",
                device=WEBCAM_MIC_INDEX,
            )
            sd.wait()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir="/tmp") as temp_file:
                wav_path = temp_file.name
                sf.write(wav_path, audio, SAMPLERATE)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Ensure file is fully written to disk

            if DEBUG:
                logger.debug(f"Captured loop sample to {wav_path}")

            event_bus.emit("EMIT_AUDIO_CAPTURED", {"path": wav_path})

        except Exception as e:
            now = time.time()
            if now - _last_error_log >= ERROR_LOG_INTERVAL:
                logger.error(f"Loop mic capture failed: {e}")
                _last_error_log = now
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
    if MIC_ENABLED:
        start_microphone()
    else:
        logger.info("Microphone listener disabled via MITCH_ENABLE_MIC=false.")
    start_keyboard()

def shutdown():
    stop_event.set()
    logger.info("Shutdown signal received. Terminating listener loops.")
