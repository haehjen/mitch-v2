import json
import os
import time
from pathlib import Path
from threading import Lock

from core.config import MITCH_ROOT
from core.event_registry import IntentRegistry
from core.peterjones import get_logger

logger = get_logger("news_digester")

KEYWORDS_PATH = Path(MITCH_ROOT) / "data" / "news_keywords.json"
HEADLINES_TXT_PATH = Path(MITCH_ROOT) / "data" / "news_headlines.txt"
HEADLINES_JSON_PATH = Path(MITCH_ROOT) / "data" / "news_headlines.json"
INJECTION_PATH = Path(MITCH_ROOT) / "data" / "injections" / "news_digest.json"

REFRESH_SECONDS = int(float(os.getenv("MITCH_NEWS_REFRESH_SECS", "1800")))
MAX_KEYWORDS_PER_PULL = int(float(os.getenv("MITCH_NEWS_KEYWORDS_PER_PULL", "8")))
MAX_RESULTS_PER_KEYWORD = int(float(os.getenv("MITCH_NEWS_RESULTS_PER_KEYWORD", "6")))
MAX_HEADLINES_STORE = int(float(os.getenv("MITCH_NEWS_MAX_HEADLINES", "40")))
INTEREST_BUMP = float(os.getenv("MITCH_NEWS_INTEREST_BUMP", "0.2"))
MAX_WEIGHT = float(os.getenv("MITCH_NEWS_MAX_WEIGHT", "6.0"))

DEFAULT_KEYWORDS = [
    "war",
    "strike",
    "missile launch",
    "drone",
    "microsoft",
    "mod",
    "defense",
    "cyber attack",
    "nato",
    "ukraine",
    "russia",
    "china",
]


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _news_search(query: str, max_results: int):
    try:
        from modules.web_search import ddgs_news_search
    except Exception as e:
        logger.warning(f"News search backend unavailable: {e}")
        return []
    try:
        return ddgs_news_search(query, max_results=max_results) or []
    except Exception as e:
        logger.warning(f"News search failed for query '{query}': {e}")
        return []


class NewsDigester:
    def __init__(self):
        self._lock = Lock()
        self._last_refresh = 0.0
        self._keywords = []
        self._headlines = []
        self._load_or_init_keywords()
        self._load_headlines_cache()

    def _load_or_init_keywords(self):
        KEYWORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not KEYWORDS_PATH.exists():
            payload = {
                "keywords": [{"term": term, "weight": 1.0, "mentions": 0} for term in DEFAULT_KEYWORDS]
            }
            KEYWORDS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        try:
            raw = json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))
            items = raw.get("keywords", []) if isinstance(raw, dict) else []
            cleaned = []
            for item in items:
                if isinstance(item, str):
                    cleaned.append({"term": item.strip().lower(), "weight": 1.0, "mentions": 0})
                    continue
                if not isinstance(item, dict):
                    continue
                term = str(item.get("term", "")).strip().lower()
                if not term:
                    continue
                cleaned.append(
                    {
                        "term": term,
                        "weight": float(item.get("weight", 1.0)),
                        "mentions": int(item.get("mentions", 0)),
                    }
                )
            self._keywords = cleaned
        except Exception as e:
            logger.warning(f"Failed loading news keywords, reinitializing defaults: {e}")
            self._keywords = [{"term": term, "weight": 1.0, "mentions": 0} for term in DEFAULT_KEYWORDS]
            self._save_keywords()

    def _save_keywords(self):
        payload = {"keywords": self._keywords}
        KEYWORDS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_headlines_cache(self):
        if not HEADLINES_JSON_PATH.exists():
            self._headlines = []
            return
        try:
            raw = json.loads(HEADLINES_JSON_PATH.read_text(encoding="utf-8"))
            self._headlines = raw.get("headlines", []) if isinstance(raw, dict) else []
        except Exception as e:
            logger.warning(f"Failed loading cached headlines: {e}")
            self._headlines = []

    def _save_headlines(self):
        payload = {
            "updated_at": _utc_now_iso(),
            "headlines": self._headlines[:MAX_HEADLINES_STORE],
        }
        HEADLINES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEADLINES_JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        lines = [f"News headlines snapshot ({payload['updated_at']} UTC)", ""]
        for idx, item in enumerate(payload["headlines"], 1):
            title = item.get("title", "").strip()
            source = item.get("source", "unknown")
            keyword = item.get("keyword", "")
            date = item.get("date", "")
            url = item.get("url", "")
            lines.append(f"{idx}. {title}")
            lines.append(f"   source: {source}")
            if date:
                lines.append(f"   date: {date}")
            if keyword:
                lines.append(f"   keyword: {keyword}")
            if url:
                lines.append(f"   url: {url}")
            lines.append("")
        HEADLINES_TXT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        INJECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
        INJECTION_PATH.write_text(
            json.dumps(
                {
                    "type": "news_digest",
                    "content": {
                        "updated_at": payload["updated_at"],
                        "headlines_count": len(payload["headlines"]),
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _top_keywords(self):
        ranked = sorted(self._keywords, key=lambda x: x.get("weight", 1.0), reverse=True)
        return ranked[:MAX_KEYWORDS_PER_PULL]

    def bump_interest_from_text(self, text: str):
        t = str(text or "").lower()
        if not t:
            return

        changed = False
        with self._lock:
            for item in self._keywords:
                term = item.get("term", "")
                if term and term in t:
                    item["mentions"] = int(item.get("mentions", 0)) + 1
                    item["weight"] = min(MAX_WEIGHT, float(item.get("weight", 1.0)) + INTEREST_BUMP)
                    changed = True
            if changed:
                self._save_keywords()

    def refresh_news(self, force: bool = False):
        now = time.time()
        if not force and now - self._last_refresh < max(5, REFRESH_SECONDS):
            return

        with self._lock:
            self._last_refresh = now
            top_keywords = self._top_keywords()
            seen = set()
            merged = []

            for kw in top_keywords:
                term = kw.get("term", "").strip()
                if not term:
                    continue
                query = f"{term} latest"
                results = _news_search(query, max_results=MAX_RESULTS_PER_KEYWORD)
                for r in results:
                    title = str(r.get("title", "")).strip()
                    url = str(r.get("url", "")).strip()
                    key = (title.lower(), url.lower())
                    if not title or key in seen:
                        continue
                    seen.add(key)
                    merged.append(
                        {
                            "title": title,
                            "url": url,
                            "source": str(r.get("source", "unknown")).strip() or "unknown",
                            "date": str(r.get("date", "")).strip(),
                            "body": str(r.get("body", "")).strip(),
                            "keyword": term,
                            "keyword_weight": float(kw.get("weight", 1.0)),
                        }
                    )

            merged.sort(key=lambda x: x.get("keyword_weight", 1.0), reverse=True)
            self._headlines = merged[:MAX_HEADLINES_STORE]
            self._save_headlines()
            logger.info(
                f"News refresh complete: keywords={len(top_keywords)} headlines={len(self._headlines)}"
            )

    def render_for_prompt(self, max_items: int = 20) -> str:
        if not self._headlines:
            return "No headlines are available yet."
        lines = []
        for idx, item in enumerate(self._headlines[:max_items], 1):
            lines.append(
                f"{idx}. {item.get('title','')} | source={item.get('source','unknown')} "
                f"| date={item.get('date','')} | keyword={item.get('keyword','')}"
            )
            url = item.get("url", "")
            if url:
                lines.append(f"   url: {url}")
            body = item.get("body", "")
            if body:
                lines.append(f"   note: {body[:240]}")
        return "\n".join(lines)


news = NewsDigester()
_bus_ref = None


def _emit_refresh_status():
    _bus_ref.emit(
        "EMIT_SPEAK",
        {
            "token": f"news_refresh_{str(time.time()).replace('.', '')}",
            "source": "news_digester",
            "text": "News headlines updated.",
        },
    )


def _handle_news_digest(_text: str):
    news.refresh_news(force=False)
    headlines_text = news.render_for_prompt(max_items=20)
    prompt = (
        "News digest request.\n\n"
        "Using the collected headlines below, give a conversational rundown with:\n"
        "- top priority stories first\n"
        "- one short section for defense/geopolitics\n"
        "- one short section for tech/business\n"
        "- one short section for what changed since last check\n"
        "- close with 3 quick follow-up options\n\n"
        f"Collected headlines:\n{headlines_text}"
    )
    _bus_ref.emit(
        "EMIT_CHAT_REQUEST",
        {
            "prompt": prompt,
            "request_type": "news_digest",
            "force_openai_minimal": False,
        },
    )


def _handle_refresh_news(_text: str):
    news.refresh_news(force=True)
    _emit_refresh_status()


def _on_conversation_event(data):
    if not isinstance(data, dict):
        return
    if str(data.get("role", "")).lower() != "user":
        return
    news.bump_interest_from_text(str(data.get("text", "")))


def _on_heartbeat(_data):
    news.refresh_news(force=False)


def start_module(event_bus):
    global _bus_ref
    _bus_ref = event_bus

    event_bus.subscribe("CONVERSATION_EVENT", _on_conversation_event)
    event_bus.subscribe("ECHO_HEARTBEAT", _on_heartbeat)

    IntentRegistry.register_intent(
        "news_digest",
        _handle_news_digest,
        keywords=["news digest", "news_digest", "daily rundown", "news rundown"],
        objects=[],
        priority=40,
    )

    IntentRegistry.register_intent(
        "news_refresh",
        _handle_refresh_news,
        keywords=["refresh news", "update news headlines", "pull news now"],
        objects=[],
        priority=35,
    )

    try:
        news.refresh_news(force=False)
    except Exception as e:
        logger.warning(f"Initial news refresh skipped: {e}")

    logger.info("NewsDigester started. Intents: news_digest, news_refresh")
