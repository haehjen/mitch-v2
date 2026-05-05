from ddgs import DDGS
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger
from core.event_registry import IntentRegistry

logger = get_logger("innermono")

LOG_PATH = os.path.join(MITCH_ROOT, 'logs', 'innermono.log')
INJECTION_PATH = os.path.join(MITCH_ROOT, 'data/injections/web_summary.md')

def log(message: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    logger.info(f"[{ts}] {message}")

def clean_query(raw: str) -> str:
    """Strip filler phrases for more accurate web queries."""
    cleaned = re.sub(
        r'\b(search|google|look for|find|news on|news about|on internet|web|latest on|tell me about|show me|what\'s|whats)\b',
        '',
        raw,
        flags=re.I
    )
    return re.sub(r'\s+', ' ', cleaned).strip()

def fetch_results(query: str) -> tuple[str, str]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))
            top_lines = []
            first_url = ""
            for r in results:
                if not isinstance(r, dict):
                    continue
                href = str(r.get("href") or r.get("url") or "").strip()
                title = str(r.get("title") or "").strip()
                body = str(r.get("body") or "").strip()
                if not first_url and href:
                    first_url = href
                line = body or title
                if line:
                    top_lines.append(line)
                if len(top_lines) >= 3:
                    break
            summary = " | ".join(top_lines) if top_lines else "No relevant results found."
            return summary, first_url
    except Exception as e:
        return f"Search failed: {e}", ""

def ddgs_news_search(query: str, max_results: int = 10) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = ddgs.news(query)
            return [r for r in results][:max_results]
    except Exception as e:
        log(f"News search failed: {e}")
        return []

def inject_summary(query: str, summary: str) -> None:
    try:
        with open(INJECTION_PATH, "w", encoding="utf-8") as f:
            f.write(f"### Web Search Summary: '{query}'\n\n{summary}\n")
        log(f"Injected summary into {INJECTION_PATH}")
    except Exception as e:
        log(f"Failed to write injection file: {e}")

def handle_web_search(event):
    raw_query = event.get('query', '').strip()
    if not raw_query:
        return

    query = clean_query(re.sub(r'^web_search\s+', '', raw_query, flags=re.I))
    log(f"Query: {query}")
    summary, top_url = fetch_results(query)
    log(f"Summary: {summary}")
    if top_url:
        log(f"Top URL: {top_url}")

    inject_summary(query, summary)

    event_bus.emit(
        "EMIT_TOOL_RESULT",
        {
            "function_name": "web_search",
            "output": {
                "query": query,
                "summary": summary,
                "top_url": top_url,
            },
        },
    )

    if top_url:
        event_bus.emit("EMIT_OPEN_URL", {"url": top_url, "source": "web_search"})

def start_module(event_bus):
    log('Web search module started')
    event_bus.subscribe('EMIT_WEB_SEARCH', handle_web_search)

    def web_search_handler(text):
        query = clean_query(text)
        event_bus.emit("EMIT_WEB_SEARCH", {"query": query})

    IntentRegistry.register_intent(
        name="web_search",
        handler=web_search_handler,
        keywords=["search", "google", "lookup", "find", "web", "news", "information"],
        objects=[]
    )
