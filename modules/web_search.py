import requests
import os
import re
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

logger = get_logger("innermono")  # Changed logger name

SEARCH_API = 'https://api.duckduckgo.com/'
LOG_PATH = os.path.join(MITCH_ROOT, 'logs', 'innermono.log')  # Updated path

def log(message: str) -> None:
    logger.info(message)

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
        resp = requests.get(
            SEARCH_API,
            params={'q': query, 'format': 'json', 'no_redirect': '1', 'no_html': '1'},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []

            for item in data.get('RelatedTopics', []):
                if isinstance(item, dict) and 'Text' in item:
                    results.append(item['Text'])
                elif 'Topics' in item:
                    for sub in item['Topics']:
                        if 'Text' in sub:
                            results.append(sub['Text'])
                        if len(results) >= 3:
                            break
                if len(results) >= 3:
                    break

            if not results and data.get('AbstractText'):
                results.append(data['AbstractText'])

            return ' | '.join(results) if results else 'No relevant results.'
        return f"Search API error {resp.status_code}."
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
