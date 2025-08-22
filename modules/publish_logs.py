import threading
import time
import json
from pathlib import Path
from datetime import datetime
from core.event_bus import event_bus
from core.config import MITCH_ROOT

DIGEST_INTERVAL = 30
OUTPUT_PATH = Path(MITCH_ROOT) / "data/recent_digest.json"
KNOWLEDGE_PATH = Path(MITCH_ROOT) / "data/knowledge.json"
MEMORY_PATH = Path(MITCH_ROOT) / "data/memory.jsonl"
INSPECTION_PATH = Path(MITCH_ROOT) / "logs/inspection_digest.json"
INNERMONO_PATH = Path(MITCH_ROOT) / "logs/innermono.log"

class DigestPublisherThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()

    def shutdown(self):
        self._stop_event.set()
        print("[DigestPublisher] Shutdown signal received.")

    def read_tail(self, path, limit):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return lines[-limit:]
        except Exception as e:
            return [f"[Error reading {path.name}: {e}]"]

    def build_digest(self):
        digest = {
            "timestamp": datetime.utcnow().isoformat(),
            "knowledge": [],
            "memory": [],
            "inspection": {},
            "innermono": []
        }

        if KNOWLEDGE_PATH.exists():
            try:
                digest["knowledge"] = json.loads(KNOWLEDGE_PATH.read_text("utf-8"))[-8:]
            except Exception as e:
                digest["knowledge"] = [f"Error: {e}"]

        if MEMORY_PATH.exists():
            digest["memory"] = self.read_tail(MEMORY_PATH, 8)

        if INSPECTION_PATH.exists():
            try:
                digest["inspection"] = json.loads(INSPECTION_PATH.read_text("utf-8"))
            except Exception as e:
                digest["inspection"] = {"error": str(e)}

        if INNERMONO_PATH.exists():
            digest["innermono"] = self.read_tail(INNERMONO_PATH, 15)

        return digest

    def run(self):
        print("[DigestPublisher] Thread started.")
        while not self._stop_event.is_set():
            digest = self.build_digest()
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(digest, f, indent=2)
            event_bus.emit("EMIT_PUBLISH_DIGEST", digest)
            self._stop_event.wait(DIGEST_INTERVAL)


def start_module(event_bus):
    thread = DigestPublisherThread()
    thread.start()
    print("[DigestPublisher] Module started and publishing digest every 4800s.")