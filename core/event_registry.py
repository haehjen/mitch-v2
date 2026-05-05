import os
import json
import re
import logging
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime
from threading import Lock
from core.config import MITCH_ROOT

REGISTRY_LOG_PATH = os.path.join(MITCH_ROOT, "data/injections", "event_registry.json")
INTENT_GUARD_LOG_PATH = os.path.join(MITCH_ROOT, "logs", "intent_guard.log")


def _intent_guard_logger():
    logger = logging.getLogger("intent_guard")
    if logger.handlers:
        return logger
    os.makedirs(os.path.dirname(INTENT_GUARD_LOG_PATH), exist_ok=True)
    handler = logging.FileHandler(INTENT_GUARD_LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


_INTENT_GUARD = _intent_guard_logger()

GENERIC_INTENT_TERMS = {
    "add", "create", "set", "task", "goal", "show", "list", "check", "get", "do",
    "help", "info", "information", "find", "search", "update", "change", "new",
    "make", "tell", "what", "how", "please", "can", "could", "would", "should",
}

STRICT_INTENT_MODULE_ALLOWLIST = {
    part.strip()
    for part in os.getenv(
        "MITCH_INTENT_GUARD_ALLOWLIST",
        (
            "modules.weather_fetcher,modules.web_search,modules.proxmon,"
            "modules.news_digester,modules.task_automator,modules.goal_tracker,"
            "modules.user_prompt_inbox,modules.tarkov_wiki_intent"
        ),
    ).split(",")
    if part.strip()
}

DISABLE_CONTEXTUAL_INTENTS = os.getenv(
    "MITCH_DISABLE_CONTEXTUAL_INTENTS", "1"
).lower() in {"1", "true", "yes"}

CONTEXTUAL_INTENT_MODULE_ALLOWLIST = {
    part.strip()
    for part in os.getenv("MITCH_CONTEXTUAL_INTENT_ALLOWLIST", "").split(",")
    if part.strip()
}

MIN_INTENT_SCORE = int(os.getenv("MITCH_MIN_INTENT_SCORE", "26"))
INTENT_PRIORITY_WEIGHT = float(os.getenv("MITCH_INTENT_PRIORITY_WEIGHT", "0.6"))
INTENT_PRIORITY_CAP = int(os.getenv("MITCH_INTENT_PRIORITY_CAP", "35"))


def _keyword_is_too_generic(keyword: str) -> bool:
    norm = Intent._normalize_text(keyword)
    if not norm:
        return True
    toks = norm.split()
    if len(toks) == 1 and toks[0] in GENERIC_INTENT_TERMS:
        return True
    if len(toks) <= 2 and all(tok in GENERIC_INTENT_TERMS for tok in toks):
        return True
    return False


class EventRegistry:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self.registry = defaultdict(lambda: {"emitters": set(), "subscribers": set()})
        self.load_registry()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def record_emit(self, event_name, source):
        self.registry[event_name]["emitters"].add(source)
        self.save_registry()

    def record_subscribe(self, event_name, subscriber):
        self.registry[event_name]["subscribers"].add(subscriber)
        self.save_registry()

    def get_all_events(self):
        return list(self.registry.keys())

    def get_emitters_for(self, event_name):
        return list(self.registry[event_name]["emitters"])

    def get_subscribers_for(self, event_name):
        return list(self.registry[event_name]["subscribers"])

    def save_registry(self):
        with open(REGISTRY_LOG_PATH, "w") as f:
            json.dump({k: {
                "emitters": list(v["emitters"]),
                "subscribers": list(v["subscribers"])
            } for k, v in self.registry.items()}, f, indent=2)

    def load_registry(self):
        if os.path.exists(REGISTRY_LOG_PATH):
            try:
                with open(REGISTRY_LOG_PATH, "r") as f:
                    data = json.load(f)
                    for event, info in data.items():
                        self.registry[event]["emitters"].update(info.get("emitters", []))
                        self.registry[event]["subscribers"].update(info.get("subscribers", []))
            except Exception as e:
                print(f"[EventRegistry] Failed to load registry: {e}")


class Intent:
    def __init__(self, name, handler, keywords=None, objects=None, priority=0):
        self.name = name
        self.handler = handler
        self.keywords = keywords or []
        self.objects = objects or []
        self.priority = int(priority or 0)

    def score(self, text):
        text = self._normalize_text(text)
        if not text or not any(c.isalpha() for c in text):
            return -1

        text_tokens = text.split()
        text_token_set = set(text_tokens)
        score = 0

        for kw in self.keywords:
            norm_kw = self._normalize_text(kw)
            if not norm_kw:
                continue
            kw_tokens = norm_kw.split()
            kw_len = len(kw_tokens)
            kw_score = 0

            if text == norm_kw:
                kw_score = max(kw_score, 90 + (kw_len * 8))

            if re.search(rf"(?<![a-z0-9]){re.escape(norm_kw)}(?![a-z0-9])", text):
                kw_score = max(kw_score, 48 + (kw_len * 6))

            overlap = sum(1 for tok in kw_tokens if tok in text_token_set)
            ratio = (overlap / kw_len) if kw_len else 0.0
            in_order = self._contains_tokens_in_order(text_tokens, kw_tokens)

            if kw_len == 1 and overlap == 1:
                kw_score = max(kw_score, 20)
            elif overlap >= 2 and ratio >= 0.75:
                # Weighted overlap captures human speech with fillers:
                # "play ... on youtube" still maps to keyword "play on youtube".
                overlap_score = 14 + (overlap * 6) + int(ratio * 10)
                if in_order:
                    overlap_score += 6
                kw_score = max(kw_score, overlap_score)

            if kw_len >= 2 and overlap == kw_len and in_order:
                kw_score = max(kw_score, 32 + (kw_len * 5))

            if kw_len >= 2 and len(text_tokens) >= 2:
                fuzzy = self._best_window_similarity(text_tokens, kw_tokens)
                if fuzzy >= 0.90:
                    kw_score = max(kw_score, 34 + (kw_len * 4))
                elif fuzzy >= 0.86:
                    kw_score = max(kw_score, 26 + (kw_len * 3))

            score += kw_score

        return score

    @staticmethod
    def _contains_tokens_in_order(text_tokens, kw_tokens):
        if not kw_tokens:
            return False
        pos = 0
        for tok in kw_tokens:
            found = False
            while pos < len(text_tokens):
                if text_tokens[pos] == tok:
                    found = True
                    pos += 1
                    break
                pos += 1
            if not found:
                return False
        return True

    @staticmethod
    def _best_window_similarity(text_tokens, kw_tokens):
        k = len(kw_tokens)
        if k == 0:
            return 0.0
        if len(text_tokens) < k:
            return 0.0
        kw_joined = " ".join(kw_tokens)
        best = 0.0
        for i in range(0, len(text_tokens) - k + 1):
            win = " ".join(text_tokens[i:i + k])
            sim = SequenceMatcher(a=kw_joined, b=win).ratio()
            if sim > best:
                best = sim
            if best >= 0.98:
                break
        return best

    @staticmethod
    def _normalize_text(text):
        text = str(text or "").lower()
        text = re.sub(r"[_\-/]+", " ", text)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


class IntentRegistry:
    intents = []

    @classmethod
    def register_intent(cls, name, handler, keywords=None, objects=None, priority=0):
        source_module = getattr(handler, "__module__", "unknown")
        keywords = keywords or []

        if (
            DISABLE_CONTEXTUAL_INTENTS
            and source_module.startswith("modules.contextual_")
            and source_module not in CONTEXTUAL_INTENT_MODULE_ALLOWLIST
        ):
            _INTENT_GUARD.info(
                "Skipped contextual intent '%s' from %s (contextual intents disabled).",
                name,
                source_module,
            )
            return

        if source_module not in STRICT_INTENT_MODULE_ALLOWLIST:
            filtered = []
            rejected = []
            for kw in keywords:
                kws = str(kw or "").strip()
                if not kws:
                    rejected.append(kws)
                    continue
                if _keyword_is_too_generic(kws):
                    rejected.append(kws)
                    continue
                filtered.append(kws)
            if rejected:
                _INTENT_GUARD.info(
                    "Rejected generic keywords for intent '%s' from %s: %s",
                    name,
                    source_module,
                    rejected,
                )
            keywords = filtered

        if not keywords:
            _INTENT_GUARD.info(
                "Skipped intent '%s' from %s (no valid keywords after guard).",
                name,
                source_module,
            )
            return

        cls.intents.append(Intent(name, handler, keywords, objects, priority=priority))

    @classmethod
    def match_intent(cls, text):
        best_intent = None
        best_rank = None
        best_score = -1
        for intent in cls.intents:
            score = intent.score(text)
            if score <= 0:
                continue
            priority_bonus = int(intent.priority * INTENT_PRIORITY_WEIGHT)
            priority_bonus = max(-INTENT_PRIORITY_CAP, min(INTENT_PRIORITY_CAP, priority_bonus))
            rank = (score + priority_bonus, score, intent.priority)
            if best_rank is None or rank > best_rank:
                best_intent = intent
                best_rank = rank
                best_score = score

        if best_intent is None:
            return None

        if best_score < MIN_INTENT_SCORE:
            return None
        return best_intent


# === Optional example intents (disabled by default) ===
# Keep demo intents opt-in so they never shadow real module handlers.
if os.getenv("MITCH_ENABLE_EXAMPLE_INTENTS", "0").lower() in {"1", "true", "yes"}:
    IntentRegistry.register_intent(
        "launch_drone",
        lambda text: print("Launching drone..."),
        keywords=["launch", "drone"],
        priority=-100,
    )

    IntentRegistry.register_intent(
        "get_weather",
        lambda text: print("Fetching weather..."),
        keywords=["weather", "forecast"],
        priority=-100,
    )
