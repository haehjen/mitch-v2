from flask import Flask, send_from_directory, request, jsonify, Response, send_file
from flask_socketio import SocketIO, emit
from core.event_bus import event_bus
import threading
import os
import cv2
import psutil
from core.peterjones import get_logger
from pathlib import Path
import requests  # <-- added for HouseCore instruction post

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
            try:
                requests.post(
                    "https://mitch.andymitchell.online/housecore/instruction",
                    json={"instruction": full_reply},
                    timeout=5
                )
            except Exception as e:
                logger.warning(f"Failed to post to HouseCore: {e}")

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

visual_orb = VisualOrb()

def run_visual_server():
    if DEBUG:
        logger.debug("Starting visual server...")

    if not DEBUG:
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)

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
    text = request.json.get("text", "")
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
    text = request.json.get("text", "")
    if text:
        if DEBUG:
            logger.debug(f"Received chat text: {text}")
        event_bus.emit("EMIT_INPUT_RECEIVED", {"text": text, "source": "user"})
    return jsonify({"status": "ok"})

@app.route("/housecore/ping", methods=["POST"])
def housecore_ping():
    data = request.get_json()
    identity = data.get("identity")
    hostname = data.get("hostname")
    logger.info(f"Ping received from {identity} ({hostname})")
    return jsonify({"status": "acknowledged"})

@app.route("/housecore/event", methods=["POST"])
def housecore_event():
    data = request.get_json()
    event_type = data.get("event")
    payload = data.get("payload", {})

    if DEBUG:
        logger.info(f"HouseCore event received: {event_type} | {payload}")

    event_bus.emit(event_type, payload)
    return jsonify({"status": "emitted"})

@app.route("/housecore/instruction", methods=["POST"])
def housecore_instruction():
    data = request.get_json()
    instruction = data.get("instruction")

    with open("/tmp/housecore_instruction.json", "w") as f:
        import json
        json.dump({"instruction": instruction}, f)

    logger.info(f"Instruction queued for HouseCore: {instruction}")
    return jsonify({"status": "queued"})

@app.route("/housecore/instruction", methods=["GET"])
def get_instruction():
    import os
    import json

    try:
        with open("/tmp/housecore_instruction.json", "r") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify({})

@app.route("/digest", methods=["GET"])
def serve_digest():
    digest_path = Path("/home/triad/mitch/data/recent_digest.json")
    if digest_path.exists():
        return send_file(str(digest_path), mimetype="application/json")
    else:
        return jsonify({"error": "Digest not found."}), 404

def start_visual():
    threading.Thread(target=run_visual_server, daemon=True).start()
