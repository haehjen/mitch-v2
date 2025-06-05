import os
import queue
import threading
import wave
import time
import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import pyaudio
from collections import defaultdict
from core.event_bus import EventBus
from piper import PiperVoice
from core.config import MITCH_ROOT

# === CONFIG ===
MODEL_PATH = Path(MITCH_ROOT) / "modules/voice/en_GB-northern_english_male-medium.onnx"
CONFIG_PATH = MODEL_PATH.with_suffix(".onnx.json")
CHUNK_TRIGGER_LEN = 40
CHUNK_BREAK_CHARS = {'.', '?', '!', '\n'}

DEBUG_SPEAKER = os.getenv("MITCH_SPEAKER_DEBUG", "false").lower() == "true"

# === Speaker Class ===
class StreamMouth:
    def __init__(self):
        self.voice = PiperVoice.load(
            model_path=MODEL_PATH,
            config_path=CONFIG_PATH,
            use_cuda=False
        )
        self.audio_queue = queue.Queue()
        self.audio_lock = threading.Lock()
        self.is_playing = threading.Event()
        self.buffered_texts = defaultdict(str)
        self.last_token_spoken = None
        self.lock = threading.Lock()

        self.stream_thread = threading.Thread(target=self._audio_loop, daemon=True, name="StreamMouthAudioLoop")
        self.stream_thread.start()

    def _audio_loop(self):
        while True:
            wav_path = self.audio_queue.get()
            if wav_path is None:
                break

            if not os.path.exists(wav_path):
                if DEBUG_SPEAKER:
                    print(f"[StreamMouth] File not found: {wav_path}")
                continue

            try:
                with self.audio_lock:
                    self.is_playing.set()
                    EventBus.get_instance().emit("MUTE_EARS", {})
                    self._play_with_pyaudio(wav_path)
            except Exception as e:
                if DEBUG_SPEAKER:
                    print(f"[StreamMouth] Playback error: {e}")
            finally:
                self.is_playing.clear()
                EventBus.get_instance().emit("UNMUTE_EARS", {})
                try:
                    os.unlink(wav_path)
                except Exception as cleanup_error:
                    if DEBUG_SPEAKER:
                        print(f"[StreamMouth] Failed to delete temp file: {cleanup_error}")

    def _play_with_pyaudio(self, wav_path):
        try:
            audio_array, samplerate = sf.read(wav_path, dtype="float32")
            if audio_array.ndim > 1:
                audio_array = audio_array.mean(axis=1)

            if samplerate != 44100:
                if DEBUG_SPEAKER:
                    print(f"[StreamMouth] Resampling from {samplerate} Hz to 44100 Hz")
                resampled = np.interp(
                    np.linspace(0, len(audio_array), int(len(audio_array) * 44100 / samplerate), endpoint=False),
                    np.arange(len(audio_array)),
                    audio_array
                ).astype(np.float32)
            else:
                resampled = audio_array

            pcm_data = (resampled * 32767).astype(np.int16).tobytes()
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)
            stream.write(pcm_data)
            stream.stop_stream()
            stream.close()
            p.terminate()

            if DEBUG_SPEAKER:
                print(f"[StreamMouth] Finished playing: {wav_path}")

        except Exception as e:
            if DEBUG_SPEAKER:
                print(f"[StreamMouth] PyAudio error: {e}")

    def synthesize_and_queue(self, text):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as temp_wav:
                wav_path = temp_wav.name

            with wave.open(wav_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(22050)
                self.voice.synthesize(text, wav_file)

            if DEBUG_SPEAKER:
                print(f"[StreamMouth] Synthesized and queued audio: {wav_path}")
            self.audio_queue.put(wav_path)
        except Exception as e:
            if DEBUG_SPEAKER:
                print(f"[StreamMouth] Synthesis error: {e}")

    def speak_chunk(self, data):
        text = data.get("chunk", "")
        token = data.get("token")
        if not text or not token:
            return

        with self.lock:
            self.buffered_texts[token] += text
            current = self.buffered_texts[token]
            if self._should_emit(current):
                if DEBUG_SPEAKER:
                    print(f"[StreamMouth] Speaking buffered chunk (token={token}): {current.strip()}")
                self.synthesize_and_queue(current.strip())
                self.buffered_texts[token] = ""

    def speak_full(self, data):
        text = data.get("text", "")
        token = data.get("token")
        if not text or not token:
            if DEBUG_SPEAKER:
                print("[StreamMouth] Missing text or token; ignoring EMIT_SPEAK")
            return

        with self.lock:
            if token == self.last_token_spoken:
                if DEBUG_SPEAKER:
                    print(f"[StreamMouth] Duplicate token {token} - ignoring.")
                return
            self.last_token_spoken = token

        if DEBUG_SPEAKER:
            print(f"[StreamMouth] Speaking full (token={token}): {text}")
        self.synthesize_and_queue(text)
        EventBus.get_instance().emit("EMIT_SPEAK_END", {"token": token, "full_text": text})

    def on_speak_end(self, data):
        token = data.get("token")
        if token in self.buffered_texts:
            del self.buffered_texts[token]

    def _should_emit(self, text):
        text = text.strip()
        return len(text) >= CHUNK_TRIGGER_LEN or any(text.endswith(c) for c in CHUNK_BREAK_CHARS)

    def shutdown(self):
        self.audio_queue.put(None)

# === Init + Bindings ===
speaker = StreamMouth()

def start_stream_mouth():
    if DEBUG_SPEAKER:
        print("[StreamMouth] Unified streaming TTS module online.")
    bus = EventBus.get_instance()
    bus.subscribe("EMIT_SPEAK", speaker.speak_full)
    bus.subscribe("EMIT_SPEAK_CHUNK", speaker.speak_chunk)
    bus.subscribe("EMIT_SPEAK_END", speaker.on_speak_end)
