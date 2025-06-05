import requests
import datetime
import os
from core.event_bus import event_bus

LOG_PATH = '/home/triad/mitch/logs/web_search.log'
SEARCH_API = 'https://api.duckduckgo.com/'


def log(message: str) -> None:
    ts = datetime.datetime.utcnow().isoformat()
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"{ts} {message}\n")


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
            for item in data.get('RelatedTopics', [])[:3]:
                if isinstance(item, dict):
                    if 'Text' in item:
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
            return ' | '.join(results) if results else 'No results.'
        return f"Search API error {resp.status_code}."
    except Exception as e:
        return f"Search failed: {e}"


def handle_web_search(event):
    query = event.get('query', '').strip()
    if not query:
        return
    log(f"Query: {query}")
    summary = fetch_results(query)
    log(f"Summary: {summary}")
    event_bus.emit('EMIT_WEB_SEARCH_RESULT', {'query': query, 'summary': summary})


def start_module(event_bus):
    log('Web search module started')
    event_bus.subscribe('EMIT_WEB_SEARCH', handle_web_search)
