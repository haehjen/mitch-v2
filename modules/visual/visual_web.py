from flask import Flask, send_from_directory, request, jsonify, Response, send_file
from flask_socketio import SocketIO, emit
from core.event_bus import event_bus
import threading
import os
import cv2
import psutil
from core.peterjones import get_logger
from pathlib import Path
import requests

logger = get_logger("visual_web")

DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
ASSET_DIR = os.path.dirname(__file__)
app.static_folder = STATIC_DIR

speaking_state = False
speak_timer = None
speak_end_timer = None
last_token = None
pending_end_token = None
live_log = []

class VisualOrb:
    def __init__(self):
        self.active_token = None
        self.chunk_buffer = {}
        event_bus.subscribe("EMIT_SPEAK_CHUNK", self.on_speak_chunk)
        event_bus.subscribe("EMIT_SPEAK_END", self.on_speak_end)
        event_bus.subscribe("EMIT_VISUAL_TOKEN", self.on_visual_token)
        event_bus.subscribe("EMIT_VIDEO_FEED", self.on_video_frame)
        event_bus.subscribe("EMIT_SPEAK", self.on_speak)
        event_bus.subscribe("EMIT_TOKEN_REGISTERED", self.on_token_registered)
        event_bus.subscribe("EMIT_MAP_PIN", self.on_map_pin)  # <-- ADDED

    def on_visual_token(self, data):
        self.active_token = data.get("token")
        if DEBUG:
            logger.debug(f"Token set to: {self.active_token}")

    def on_token_registered(self, data):
        global last_token, pending_end_token
        token = data.get("token")
        last_token = token
        self.active_token = token
        if DEBUG:
            logger.debug(f"Token registered: {token}")
        if pending_end_token and pending_end_token == last_token:
            if DEBUG:
                logger.debug("Re-processing previously stale EMIT_SPEAK_END")
            self.set_speaking_state(False)
            pending_end_token = None

    def on_speak(self, data):
        global speak_timer, speak_end_timer
        token = data.get("token") if data else None
        source = data.get("source") if data else None
        if DEBUG:
            logger.debug(f"EMIT_SPEAK received (source: {source or 'default'}, token: {token})")

        if source in ("status", "internal"):
            if DEBUG:
                logger.debug(f"Ignoring EMIT_SPEAK from source: {source}")
            return

        if speak_end_timer:
            speak_end_timer.cancel()
            speak_end_timer = None

        if speak_timer:
            speak_timer.cancel()
        speak_timer = threading.Timer(0.01, self.set_speaking_state, args=(True,))
        speak_timer.start()

    def on_speak_chunk(self, data):
        chunk = data.get("chunk", "")
        token = data.get("token")
        if token != self.active_token:
            if DEBUG:
                logger.debug(f"Ignoring EMIT_SPEAK_CHUNK - stale token {token} != {self.active_token}")
            return

        if token not in self.chunk_buffer:
            self.chunk_buffer[token] = []
        self.chunk_buffer[token].append(chunk)

        socketio.emit("speak_chunk", {"chunk": chunk, "token": token})

    def on_speak_end(self, data):
        global speak_timer, speak_end_timer, last_token, pending_end_token
        token = data.get("token")
        if DEBUG:
            logger.debug(f"EMIT_SPEAK_END received (token: {token})")

        if token != last_token:
            if DEBUG:
                logger.debug(f"Ignoring EMIT_SPEAK_END - stale token {token} != {last_token}")
            pending_end_token = token
            return

        if speak_timer:
            speak_timer.cancel()
            speak_timer = None

        if speak_end_timer:
            speak_end_timer.cancel()
        speak_end_timer = threading.Timer(0.01, self.set_speaking_state, args=(False,))
        speak_end_timer.start()

        socketio.emit("speak_end", {"token": token})

        if token in self.chunk_buffer:
            full_reply = "".join(self.chunk_buffer.pop(token)).strip()
            if full_reply and DEBUG:
                logger.debug(f"Final reply to chat: {full_reply}")
            live_log.append(full_reply)

        self.active_token = None

    def on_video_frame(self, data):
        frame = data.get("frame")
        if frame:
            socketio.emit("video_frame", {"frame": frame})

    def set_speaking_state(self, value):
        global speaking_state
        speaking_state = value
        if DEBUG:
            state = "activating orb" if value else "deactivating orb"
            logger.debug(f"Finalized state update - {state}.")

    def on_map_pin(self, data):  # <-- NEW METHOD
        if not data:
            return
        lat = data.get("lat")
        lon = data.get("lon")
        label = data.get("label", "")
        description = data.get("description", "")
        if lat is None or lon is None:
            if DEBUG:
                logger.debug("EMIT_MAP_PIN missing lat/lon")
            return
        socketio.emit("EMIT_MAP_PIN", {
            "lat": lat,
            "lon": lon,
            "label": label,
            "description": description
        })
        if DEBUG:
            logger.debug(f"Forwarded pin: {label} @ {lat},{lon}")

visual_orb = VisualOrb()

# === Log streaming thread ===
import time
from threading import Thread

LOG_PATH = "/home/triad/mitch/logs/innermono.log"

def stream_innermono_log():
    try:
        with open(LOG_PATH, "r") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    socketio.emit("INNEMONO_LINE", {"line": line.strip()})
                else:
                    time.sleep(0.3)
    except Exception as e:
        print(f"[log_streamer] Failed: {e}")

def run_visual_server():
    Thread(target=stream_innermono_log, daemon=True).start()
    if DEBUG:
        logger.debug("Starting visual server...")

    if not DEBUG:
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def start_visual():
    run_visual_server()

# === Flask routes ===

@app.route("/")
def index():
    visual_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "orb.html"))
    return send_from_directory(os.path.dirname(visual_path), os.path.basename(visual_path))

@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory(STATIC_DIR, path)

@app.route("/OBJLoader.js")
def serve_objloader():
    return send_from_directory(ASSET_DIR, "OBJLoader.js")

@app.route("/main.js")
def serve_mainjs():
    return send_from_directory(ASSET_DIR, "main.js")

@app.route("/FinalBaseMesh.obj")
def serve_mesh():
    return send_from_directory(ASSET_DIR, "FinalBaseMesh.obj")

@app.route("/metrics")
def metrics():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return jsonify({
        "cpu": cpu,
        "ram": ram,
        "speaking": speaking_state
    })

@app.route("/latest.jpg")
def latest_image():
    from modules.vision import VisionModule
    vision = VisionModule()
    image_path = vision.capture_image("modules/visual/static/latest.jpg")
    return send_from_directory(os.path.dirname(image_path), os.path.basename(image_path))

@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open video device")
    while True:
        success, frame = cap.read()
        if not success:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

@app.route("/audio", methods=["POST"])
def receive_audio():
    audio_chunk = request.data
    socketio.emit("audio_chunk", {"audio": audio_chunk})
    return "", 204

@app.route("/emit_response", methods=["POST"])
def emit_response():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if text:
        live_log.append(text)
    return jsonify({"status": "ok"})

@app.route("/get_response")
def get_response():
    if live_log:
        return jsonify({"text": live_log.pop(0)})
    return jsonify({"text": ""})

@app.route("/listen", methods=["POST"])
def handle_listen():
    """Robustly accept user text and bridge to EMIT_INPUT_RECEIVED.

    Accepts JSON {text}, form field text, query param text, or raw body.
    Avoids AttributeError when request.json is None.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text") if isinstance(data, dict) else None
    if not text:
        # Fallbacks
        text = request.form.get("text") or request.args.get("text")
    if not text and request.data:
        try:
            # Try parse raw JSON
            import json as _json
            maybe = _json.loads(request.data.decode("utf-8", errors="ignore") or "{}")
            if isinstance(maybe, dict):
                text = maybe.get("text")
            if not text and isinstance(maybe, str):
                text = maybe
        except Exception:
            # Treat raw bytes as utf-8 text
            try:
                text = request.data.decode("utf-8", errors="ignore")
            except Exception:
                text = None

    text = (text or "").strip()
    if not text:
        if DEBUG:
            logger.debug("/listen received empty text payload")
        return jsonify({"error": "No text provided"}), 400

    if DEBUG:
        logger.debug(f"Received chat text: {text}")
    event_bus.emit("EMIT_INPUT_RECEIVED", {"text": text, "source": "user"})
    return jsonify({"status": "ok"})

# === File Upload handling ===
from werkzeug.utils import secure_filename
from pathlib import Path

UPLOAD_DIR = Path("/home/triad/mitch/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.route("/upload", methods=["POST"])
def handle_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    filepath = UPLOAD_DIR / filename
    file.save(str(filepath))

    file_info = {
        "filename": filename,
        "type": filename.split(".")[-1].lower(),
        "filetype": filename.split(".")[-1].lower(),
        "url": f"/uploads/{filename}"
    }

    logger.info(f"[visual_web] Upload handled: {file_info}")
    event_bus.emit("EMIT_FILE_READY", file_info)

    return jsonify(file_info)

@app.route("/uploads/<filename>")
def serve_upload(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)

# === SocketIO bridge for frontend emits ===
@socketio.on("emit_file_ready")
def handle_emit_file_ready(data):
    logger.info(f"[visual_web] Socket emit_file_ready received: {data}")
    event_bus.emit("EMIT_FILE_READY", data or {})
