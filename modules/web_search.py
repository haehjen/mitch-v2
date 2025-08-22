from ddgs import DDGS
import os
import re
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger
from datetime import datetime, timezone

logger = get_logger("innermono")

LOG_PATH = os.path.join(MITCH_ROOT, 'logs', 'innermono.log')

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

def fetch_results(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query)
            top_results = [r["body"] for r in results if "body" in r][:3]
            return ' | '.join(top_results) if top_results else "No relevant results found."
    except Exception as e:
        return f"Search failed: {e}"

def handle_web_search(event):
    raw_query = event.get('query', '').strip()
    if not raw_query:
        return
    query = clean_query(raw_query)
    log(f"Query: {query}")
    summary = fetch_results(query)
    log(f"Summary: {summary}")
    event_bus.emit('EMIT_WEB_SEARCH_RESULT', {'query': query, 'summary': summary})

def start_module(event_bus):
    log('Web search module started')
    event_bus.subscribe('EMIT_WEB_SEARCH', handle_web_search)
