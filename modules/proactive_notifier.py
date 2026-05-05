import json
import time
from pathlib import Path
from threading import Lock

from core.config import MITCH_ROOT
from core.event_registry import IntentRegistry
from core.peterjones import get_logger

logger = get_logger("proactive_notifier")

INBOX_PATH = Path(MITCH_ROOT) / "data" / "user_prompt_inbox.json"
STATE_PATH = Path(MITCH_ROOT) / "data" / "injections" / "proactive_notifier_state.json"

CHECK_INTERVAL_SECONDS = 20
ALERT_COOLDOWN_SECONDS = 300
INBOX_COOLDOWN_SECONDS = 180
SUMMARY_COOLDOWN_SECONDS = 900


def _now() -> float:
    return time.time()


def _token(prefix: str = "proactive") -> str:
    return f"{prefix}_{int(_now() * 1_000_000)}"


def _safe_text(value) -> str:
    return str(value or "").strip()


class ProactiveNotifier:
    def __init__(self):
        self._lock = Lock()
        self.enabled = True
        self.last_check_ts = 0.0
        self.last_inbox_signature = ""
        self.last_emit_by_key = {}
        self._load_state()

    def _load_state(self):
        if not STATE_PATH.exists():
            return
        try:
            payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Failed to load notifier state: {exc}")
            return

        if not isinstance(payload, dict):
            return

        self.enabled = bool(payload.get("enabled", True))
        self.last_check_ts = float(payload.get("last_check_ts", 0.0) or 0.0)
        self.last_inbox_signature = _safe_text(payload.get("last_inbox_signature", ""))
        raw_emit = payload.get("last_emit_by_key", {})
        if isinstance(raw_emit, dict):
            clean = {}
            for k, v in raw_emit.items():
                key = _safe_text(k)
                if not key:
                    continue
                try:
                    clean[key] = float(v)
                except Exception:
                    continue
            self.last_emit_by_key = clean

    def _save_state(self):
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "enabled": self.enabled,
                "last_check_ts": self.last_check_ts,
                "last_inbox_signature": self.last_inbox_signature,
                "last_emit_by_key": self.last_emit_by_key,
            }
            STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to save notifier state: {exc}")

    def _recently_emitted(self, key: str, cooldown_seconds: int) -> bool:
        ts = float(self.last_emit_by_key.get(key, 0.0) or 0.0)
        return (_now() - ts) < cooldown_seconds

    def _mark_emitted(self, key: str):
        self.last_emit_by_key[key] = _now()

    def _emit_speak(self, bus, text: str, source: str):
        spoken = _safe_text(text)
        if not spoken:
            return
        token = _token()
        bus.emit("EMIT_TOKEN_REGISTERED", {"token": token})
        bus.emit("EMIT_VISUAL_TOKEN", {"token": token})
        bus.emit(
            "EMIT_SPEAK",
            {
                "text": spoken,
                "token": token,
                "source": source,
            },
        )

    def _read_inbox_items(self):
        if not INBOX_PATH.exists():
            return []
        try:
            payload = json.loads(INBOX_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Failed to parse user_prompt_inbox.json: {exc}")
            return []
        if not isinstance(payload, dict):
            return []
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        return [x for x in items if isinstance(x, dict)]

    def check_on_heartbeat(self, bus):
        with self._lock:
            if not self.enabled:
                return

            now = _now()
            if (now - self.last_check_ts) < CHECK_INTERVAL_SECONDS:
                return
            self.last_check_ts = now

            items = self._read_inbox_items()
            pending = len(items)
            if pending <= 0:
                self.last_inbox_signature = ""
                self._save_state()
                return

            top = items[0] if items else {}
            top_id = _safe_text(top.get("id", "unknown"))
            signature = f"{pending}:{top_id}"
            changed = signature != self.last_inbox_signature

            if changed:
                emit_key = f"inbox:{signature}"
                if not self._recently_emitted(emit_key, INBOX_COOLDOWN_SECONDS):
                    msg = f"House, clutterbox has {pending} pending question{'s' if pending != 1 else ''}. Say clutterbox to review."
                    self._emit_speak(bus, msg, "proactive_notifier")
                    self._mark_emitted(emit_key)
                self.last_inbox_signature = signature

            self._save_state()

    def on_alert_triggered(self, bus, data):
        with self._lock:
            if not self.enabled:
                return
            payload = data if isinstance(data, dict) else {}
            message = _safe_text(payload.get("message") or "System alert triggered.")
            key = f"alert:{message.lower()}"
            if self._recently_emitted(key, ALERT_COOLDOWN_SECONDS):
                return
            self._emit_speak(bus, f"House, alert triggered: {message}", "proactive_notifier")
            self._mark_emitted(key)
            self._save_state()

    def on_summary_update(self, bus, data):
        with self._lock:
            if not self.enabled:
                return
            payload = data if isinstance(data, dict) else {}
            stamp = _safe_text(payload.get("timestamp") or payload.get("path") or "summary")
            key = f"summary:{stamp.lower()}"
            if self._recently_emitted("summary_global", SUMMARY_COOLDOWN_SECONDS):
                return
            self._emit_speak(bus, "House, summary digest has been refreshed.", "proactive_notifier")
            self._mark_emitted("summary_global")
            self._mark_emitted(key)
            self._save_state()

    def set_enabled(self, enabled: bool):
        with self._lock:
            self.enabled = bool(enabled)
            self._save_state()


notifier = ProactiveNotifier()
_bus_ref = None


def _handle_heartbeat(_data):
    if _bus_ref is None:
        return
    notifier.check_on_heartbeat(_bus_ref)


def _handle_alert_triggered(data):
    if _bus_ref is None:
        return
    notifier.on_alert_triggered(_bus_ref, data)


def _handle_summary_update(data):
    if _bus_ref is None:
        return
    notifier.on_summary_update(_bus_ref, data)


def _handle_proactive_toggle(text: str):
    msg = _safe_text(text).lower()
    if not _bus_ref:
        return

    if any(x in msg for x in ("off", "disable", "stop", "mute")):
        notifier.set_enabled(False)
        notifier._emit_speak(_bus_ref, "Proactive notifications disabled.", "proactive_notifier")
        return

    if any(x in msg for x in ("on", "enable", "start", "unmute")):
        notifier.set_enabled(True)
        notifier._emit_speak(_bus_ref, "Proactive notifications enabled.", "proactive_notifier")
        return

    state = "enabled" if notifier.enabled else "disabled"
    notifier._emit_speak(_bus_ref, f"Proactive notifications are currently {state}.", "proactive_notifier")


def start_module(event_bus):
    global _bus_ref
    _bus_ref = event_bus

    event_bus.subscribe("ECHO_HEARTBEAT", _handle_heartbeat)
    event_bus.subscribe("ALERT_TRIGGERED", _handle_alert_triggered)
    event_bus.subscribe("EMIT_PUBLISH_DIGEST", _handle_summary_update)
    event_bus.subscribe("inspection_digest_ready", _handle_summary_update)

    IntentRegistry.register_intent(
        "proactive_notifications_control",
        _handle_proactive_toggle,
        keywords=["proactive", "notifications"],
        objects=[],
        priority=80,
    )

    logger.info("proactive_notifier started (heartbeat + alerts + clutterbox)")
