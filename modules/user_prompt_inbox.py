import json
import re
import time
from pathlib import Path
from threading import Lock

from core.config import MITCH_ROOT
from core.event_registry import IntentRegistry
from core.peterjones import get_logger

logger = get_logger("user_prompt_inbox")

INBOX_PATH = Path(MITCH_ROOT) / "data" / "user_prompt_inbox.json"
MAX_ITEMS = 50

EXCLUDED_PHRASES = {
    "what else would you like to know about this topic?",
    "would you like to explore related topics?",
}

ACTIONABLE_PATTERNS = [
    re.compile(r"\bwould you like to set (a )?new goal\b", re.IGNORECASE),
    re.compile(r"\bdo you want to set (a )?new goal\b", re.IGNORECASE),
    re.compile(r"\bset (a )?new goal\b", re.IGNORECASE),
    re.compile(r"\bset (a )?goal\b", re.IGNORECASE),
    re.compile(r"\bdo you want me to\b", re.IGNORECASE),
    re.compile(r"\bwould you like me to\b", re.IGNORECASE),
    re.compile(r"\bshould i\b", re.IGNORECASE),
    re.compile(r"\bshould we\b", re.IGNORECASE),
    re.compile(r"\breview pending tasks\b", re.IGNORECASE),
    re.compile(r"\bheartbeat health check\b", re.IGNORECASE),
    re.compile(r"\bsummary (updates?|digest)\b", re.IGNORECASE),
    re.compile(r"\balerts? and active modules\b", re.IGNORECASE),
]

ACTIONABLE_HINTS = (
    "would you like",
    "do you want",
    "do you want me to",
    "would you like me to",
    "should i",
    "can you",
    "could you",
    "should we",
    "what goal",
)


def _new_token(prefix: str = "clutterbox") -> str:
    return f"{prefix}_{str(time.time()).replace('.', '')}"


def _normalize_text(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _is_actionable_prompt(text: str) -> bool:
    t = _normalize_text(text)
    if not t:
        return False

    lower = t.lower()
    if lower in EXCLUDED_PHRASES:
        return False

    if any(p.search(t) for p in ACTIONABLE_PATTERNS):
        return True

    if "?" in t and any(h in lower for h in ACTIONABLE_HINTS):
        return True

    return False


class UserPromptInbox:
    def __init__(self):
        self._lock = Lock()
        self._items = []
        self._review_active = False
        self._cursor = 0
        self._load()

    def _load(self):
        if not INBOX_PATH.exists():
            self._items = []
            return
        try:
            raw = json.loads(INBOX_PATH.read_text(encoding="utf-8"))
            items = raw.get("items", []) if isinstance(raw, dict) else []
            self._items = [x for x in items if isinstance(x, dict) and x.get("text")]
            self._review_active = bool(raw.get("review_active", False)) if isinstance(raw, dict) else False
            self._cursor = int(raw.get("cursor", 0)) if isinstance(raw, dict) else 0
            self._cursor = max(0, min(self._cursor, max(0, len(self._items) - 1)))
        except Exception as e:
            logger.warning(f"Failed loading inbox: {e}")
            self._items = []
            self._review_active = False
            self._cursor = 0

    def _save(self):
        INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "items": self._items[:MAX_ITEMS],
            "review_active": self._review_active,
            "cursor": self._cursor,
        }
        INBOX_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _extract_texts(self, event_name: str, data) -> list[str]:
        texts: list[str] = []

        if event_name == "SUGGESTION_READY":
            if isinstance(data, list):
                texts.extend(str(x) for x in data)
            elif isinstance(data, str):
                texts.append(data)
            return texts

        if event_name == "CONVERSATION_ENHANCED":
            if isinstance(data, dict):
                suggestions = data.get("suggestions", [])
                if isinstance(suggestions, list):
                    texts.extend(str(x) for x in suggestions)
                elif isinstance(suggestions, str):
                    texts.append(suggestions)
            elif isinstance(data, list):
                texts.extend(str(x) for x in data)
            elif isinstance(data, str):
                texts.append(data)
            return texts

        return texts

    def ingest(self, event_name: str, data):
        candidates = self._extract_texts(event_name, data)
        if not candidates:
            return

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            changed = False
            for text in candidates:
                text = _normalize_text(text)
                if not _is_actionable_prompt(text):
                    continue

                existing = next((x for x in self._items if x.get("text", "").lower() == text.lower()), None)
                if existing:
                    existing["count"] = int(existing.get("count", 1)) + 1
                    existing["last_seen"] = now
                    changed = True
                    continue

                self._items.insert(
                    0,
                    {
                        "id": _new_token("q"),
                        "text": text,
                        "source_event": event_name,
                        "created_at": now,
                        "last_seen": now,
                        "count": 1,
                    },
                )
                changed = True

            if changed:
                self._items = self._items[:MAX_ITEMS]
                self._save()

    def render(self) -> str:
        with self._lock:
            if not self._items:
                return "Clutterbox is empty. No pending questions for you right now."

            top = self._items[:8]
            lines = ["Clutterbox pending questions:"]
            for idx, item in enumerate(top, 1):
                lines.append(f"{idx}. {item.get('text', '').strip()}")
            return "\n".join(lines)

    def clear(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items = []
            self._review_active = False
            self._cursor = 0
            self._save()
            return count

    def _pending_items(self):
        return [x for x in self._items if not x.get("answered")]

    def _current_pending(self):
        pending = self._pending_items()
        if not pending:
            return None, 0, 0
        self._cursor = max(0, min(self._cursor, len(pending) - 1))
        return pending[self._cursor], self._cursor + 1, len(pending)

    def start_review(self) -> str:
        with self._lock:
            pending = self._pending_items()
            if not pending:
                self._review_active = False
                self._cursor = 0
                self._save()
                return "Clutterbox is empty. No pending questions for you right now."
            # If review is already active, keep cursor position instead of resetting to question 1.
            if not self._review_active:
                self._cursor = 0
            self._review_active = True
            item, index, total = self._current_pending()
            self._save()
            return (
                f"Clutterbox question {index} of {total}: {item.get('text','').strip()} "
                "Say 'clutterbox answer ...' to answer, or 'clutterbox next' to skip."
            )

    def answer_current(self, answer_text: str) -> str:
        with self._lock:
            if not self._review_active:
                return "Clutterbox review is not active. Say 'clutterbox' to start."

            pending = self._pending_items()
            if not pending:
                self._review_active = False
                self._cursor = 0
                self._save()
                return "No pending clutterbox questions left."

            self._cursor = max(0, min(self._cursor, len(pending) - 1))
            target = pending[self._cursor]
            target["answered"] = True
            target["answer"] = _normalize_text(answer_text)[:400]
            target["answered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            remaining = self._pending_items()
            if not remaining:
                self._review_active = False
                self._cursor = 0
                self._save()
                return "Answer saved. Clutterbox complete."

            if self._cursor >= len(remaining):
                self._cursor = len(remaining) - 1
            nxt, index, total = self._current_pending()
            self._save()
            return (
                f"Answer saved. Next question {index} of {total}: {nxt.get('text','').strip()} "
                "Say 'clutterbox answer ...' or 'clutterbox next'."
            )

    def next_question(self) -> str:
        with self._lock:
            if not self._review_active:
                return "Clutterbox review is not active. Say 'clutterbox' to start."
            pending = self._pending_items()
            if not pending:
                self._review_active = False
                self._cursor = 0
                self._save()
                return "No pending clutterbox questions left."
            self._cursor = (self._cursor + 1) % len(pending)
            item, index, total = self._current_pending()
            self._save()
            return f"Question {index} of {total}: {item.get('text','').strip()}"

    def stop_review(self) -> str:
        with self._lock:
            self._review_active = False
            self._cursor = 0
            self._save()
            return "Clutterbox review paused."

    def is_review_active(self) -> bool:
        with self._lock:
            return bool(self._review_active)

    def current_prompt(self) -> str:
        with self._lock:
            if not self._review_active:
                return "Clutterbox review is not active. Say 'clutterbox' to start."
            item, index, total = self._current_pending()
            if not item:
                self._review_active = False
                self._cursor = 0
                self._save()
                return "No pending clutterbox questions left."
            self._save()
            return (
                f"Question {index} of {total}: {item.get('text','').strip()} "
                "Say 'answer ...' or 'clutterbox next'."
            )


inbox = UserPromptInbox()


def _emit_reply(bus, text: str):
    bus.emit(
        "EMIT_SPEAK",
        {
            "text": text,
            "token": _new_token("clutterbox"),
            "source": "user_prompt_inbox",
        },
    )


def _handle_inbox_intent(text: str):
    msg = str(text or "").strip().lower()
    normalized = _normalize_text(msg)

    answer_prefixes = (
        "clutterbox answer ",
        "clutter box answer ",
        "the box answer ",
        "box answer ",
        "answer ",
    )

    if "clear" in msg:
        count = inbox.clear()
        _emit_reply(event_bus_ref, f"Clutterbox cleared. Removed {count} pending item(s).")
        return

    for prefix in answer_prefixes:
        if normalized.startswith(prefix):
            answer = _normalize_text(text)[len(prefix):].strip()
            _emit_reply(event_bus_ref, inbox.answer_current(answer))
            return

    # During active review, allow short direct replies like "yes"/"no" without strict prefix.
    if inbox.is_review_active() and normalized in {"yes", "no", "yep", "nope"}:
        _emit_reply(event_bus_ref, inbox.answer_current(normalized))
        return

    if normalized in {"clutterbox next", "clutterbox skip"}:
        _emit_reply(event_bus_ref, inbox.next_question())
        return
    if normalized in {"clutterbox done", "clutterbox stop", "clutterbox exit"}:
        _emit_reply(event_bus_ref, inbox.stop_review())
        return
    if normalized in {"clutterbox list", "show clutterbox", "show clutter box"}:
        _emit_reply(event_bus_ref, inbox.render())
        return
    if inbox.is_review_active():
        _emit_reply(event_bus_ref, inbox.current_prompt())
        return
    _emit_reply(event_bus_ref, inbox.start_review())


def _on_suggestion_ready(data):
    inbox.ingest("SUGGESTION_READY", data)


def _on_conversation_enhanced(data):
    inbox.ingest("CONVERSATION_ENHANCED", data)


event_bus_ref = None


def start_module(event_bus):
    global event_bus_ref
    event_bus_ref = event_bus

    event_bus.subscribe("SUGGESTION_READY", _on_suggestion_ready)
    event_bus.subscribe("CONVERSATION_ENHANCED", _on_conversation_enhanced)

    IntentRegistry.register_intent(
        "clutterbox_inbox",
        _handle_inbox_intent,
        keywords=[
            "clutterbox",
            "clutter box",
            "the box",
            "show clutterbox",
            "show clutter box",
            "clutterbox answer",
            "box answer",
            "the box answer",
            "clutterbox next",
            "clutterbox skip",
            "clutterbox done",
            "clutterbox stop",
            "clutterbox exit",
            "clutterbox list",
        ],
        objects=[],
        priority=90,
    )

    logger.info("user_prompt_inbox started (trigger: clutterbox)")
