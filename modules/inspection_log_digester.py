import json
from pathlib import Path
from datetime import datetime
from core.event_bus import event_bus
from core.config import MITCH_ROOT

LOG_DIR = Path(MITCH_ROOT) / "logs"
DIGEST_FILE = LOG_DIR / "inspection_digest.json"
MAX_BYTES_PER_LOG = 5000
MAX_LOGS = 30

def summarize_log(content):
    lines = content.strip().splitlines()
    snippet = "\n".join(lines[:10])
    return snippet if snippet else "Log contained no data."

def extract_digest():
    logs = sorted(LOG_DIR.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    digest = {}

    for log in logs[:MAX_LOGS]:
        try:
            content = log.read_text(encoding="utf-8")[:MAX_BYTES_PER_LOG]
            digest[log.name] = {
                "timestamp": datetime.fromtimestamp(log.stat().st_mtime).isoformat(),
                "summary": summarize_log(content)
            }
        except Exception as e:
            digest[log.name] = {
                "timestamp": datetime.now().isoformat(),
                "summary": f"[Error reading log: {e}]"
            }

    return digest

def save_digest(digest):
    DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_FILE.write_text(json.dumps(digest, indent=2), encoding="utf-8")

def start_module(event_bus):
    print("[LogDigester] Running inspection digest pass...")
    digest = extract_digest()
    save_digest(digest)
    print(f"[LogDigester] Saved digest to {DIGEST_FILE}")
    event_bus.emit("inspection_digest_ready", {"path": str(DIGEST_FILE)})
