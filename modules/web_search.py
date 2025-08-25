from ddgs import DDGS
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

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

def fetch_results(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query)
            top_results = [r["body"] for r in results if "body" in r][:3]
            return ' | '.join(top_results) if top_results else "No relevant results found."
    except Exception as e:
        return f"Search failed: {e}"

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

    query = clean_query(raw_query)
    log(f"Query: {query}")
    summary = fetch_results(query)
    log(f"Summary: {summary}")

    inject_summary(query, summary)

    # Generate a consistent token for this interaction
    token = f"tool_websearch_{int(time.time() * 1000)}"

    # Register the token visually/logically
    event_bus.emit("EMIT_TOKEN_REGISTERED", {"token": token})
    event_bus.emit("EMIT_VISUAL_TOKEN", {"token": token})

    # Stream the message as a single chunk
    message = f"Here’s what I found about '{query}': {summary}"
    event_bus.emit("EMIT_SPEAK_CHUNK", {"chunk": message, "token": token})
    event_bus.emit("EMIT_SPEAK_END", {"token": token, "full_text": summary})

    # Optionally emit for other UI listeners (not for voice)
    event_bus.emit("EMIT_CHAT_RESPONSE", {
        "tool": "web_search",
        "query": query,
        "summary": summary,
        "text": message,
        "token": token
    })

def start_module(event_bus):
    log('Web search module started')
    event_bus.subscribe('EMIT_WEB_SEARCH', handle_web_search)
