import base64
import os
import socket
import threading
import time
from urllib.parse import urlparse

import cv2
from core.peterjones import get_logger

logger = get_logger("rtsp_stream")

RTSP_ENABLED = os.getenv("MITCH_ENABLE_RTSP", "true").lower() == "true"
RTSP_URL = os.getenv("MITCH_RTSP_URL", "rtsp://192.168.4.133:554/live/ch00_0")
EMIT_FPS = float(os.getenv("MITCH_RTSP_EMIT_FPS", "6"))
RECONNECT_DELAY = float(os.getenv("MITCH_RTSP_RECONNECT_DELAY", "2.0"))
MAX_RECONNECT_DELAY = float(os.getenv("MITCH_RTSP_MAX_RECONNECT_DELAY", "30.0"))
WARN_INTERVAL = float(os.getenv("MITCH_RTSP_WARN_INTERVAL", "30.0"))
CONNECTIVITY_TIMEOUT = float(os.getenv("MITCH_RTSP_CONNECTIVITY_TIMEOUT", "2.0"))


class RTSPStream:
    def __init__(self, url: str):
        self.url = url
        self._lock = threading.Lock()
        self._latest_jpeg = None
        self._last_frame_ts = 0.0
        self._running = False
        self._thread = None
        self._bus = None
        self._last_warn_ts = 0.0

    def start(self, bus=None):
        if not RTSP_ENABLED:
            logger.info("RTSP stream disabled via MITCH_ENABLE_RTSP=false.")
            return
        if self._running:
            return
        self._bus = bus
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="rtsp_stream_loop")
        self._thread.start()
        logger.info(f"RTSP stream started: {self.url}")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=2)
            except KeyboardInterrupt:
                logger.warning("RTSP shutdown interrupted; forcing stop without waiting.")

    def get_latest_jpeg(self):
        with self._lock:
            return self._latest_jpeg

    def last_frame_timestamp(self) -> float:
        with self._lock:
            return self._last_frame_ts

    def _open_capture(self):
        cap = cv2.VideoCapture(self.url)
        if not cap.isOpened() and hasattr(cv2, "CAP_FFMPEG"):
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        return cap

    def _host_reachable(self) -> bool:
        try:
            parsed = urlparse(self.url)
            host = parsed.hostname
            port = parsed.port or 554
            if not host:
                return False
            with socket.create_connection((host, port), timeout=CONNECTIVITY_TIMEOUT):
                return True
        except Exception:
            return False

    def _loop(self):
        next_emit = 0.0
        cap = None
        reconnect_delay = RECONNECT_DELAY
        while self._running:
            if not self._host_reachable():
                now = time.time()
                if now - self._last_warn_ts >= WARN_INTERVAL:
                    logger.warning("RTSP host unreachable; retrying...")
                    self._last_warn_ts = now
                time.sleep(reconnect_delay)
                reconnect_delay = min(MAX_RECONNECT_DELAY, reconnect_delay * 1.5)
                continue

            if cap is None or not cap.isOpened():
                cap = self._open_capture()
                if not cap.isOpened():
                    now = time.time()
                    if now - self._last_warn_ts >= WARN_INTERVAL:
                        logger.warning("RTSP stream not available; retrying...")
                        self._last_warn_ts = now
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(MAX_RECONNECT_DELAY, reconnect_delay * 1.5)
                    continue

            ok, frame = cap.read()
            if not ok:
                now = time.time()
                if now - self._last_warn_ts >= WARN_INTERVAL:
                    logger.warning("RTSP read failed; reconnecting...")
                    self._last_warn_ts = now
                cap.release()
                cap = None
                time.sleep(reconnect_delay)
                reconnect_delay = min(MAX_RECONNECT_DELAY, reconnect_delay * 1.5)
                continue
            reconnect_delay = RECONNECT_DELAY

            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                continue

            jpeg_bytes = buf.tobytes()
            now = time.time()
            with self._lock:
                self._latest_jpeg = jpeg_bytes
                self._last_frame_ts = now

            if self._bus and EMIT_FPS > 0 and now >= next_emit:
                b64 = base64.b64encode(jpeg_bytes).decode("ascii")
                payload = {"frame": f"data:image/jpeg;base64,{b64}"}
                self._bus.emit("EMIT_VIDEO_FEED", payload)
                next_emit = now + (1.0 / EMIT_FPS)

        if cap:
            cap.release()


_stream_instance = None
_stream_lock = threading.Lock()


def get_rtsp_stream():
    global _stream_instance
    with _stream_lock:
        if _stream_instance is None:
            _stream_instance = RTSPStream(RTSP_URL)
        return _stream_instance


def start_module(bus):
    stream = get_rtsp_stream()
    stream.start(bus)


def shutdown():
    stream = get_rtsp_stream()
    stream.stop()
