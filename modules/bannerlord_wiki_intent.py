import re
from html import unescape
from urllib.parse import unquote

import requests
from ddgs import DDGS

from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger

logger = get_logger("bannerlord_wiki_intent")

EVENT_NAME = "EMIT_BANNERLORD_WIKI_QUERY"
SEARCH_DOMAINS = (
    "mountandblade.fandom.com",
    "mountandblade2bannerlord.wiki.fextralife.com",
)
DOMAIN_API_ENDPOINTS = {
    "mountandblade.fandom.com": "https://mountandblade.fandom.com/api.php",
}
SEARCH_TIMEOUT_SECONDS = 10
PAGE_TIMEOUT_SECONDS = 10
MAX_SNIPPET_CHARS = 1800
MAX_QUERY_TERMS = 8
MIN_RESULT_SCORE = 22

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "do", "for", "from", "how",
    "i", "in", "is", "it", "me", "of", "on", "or", "tell", "the", "to", "what",
    "when", "where", "which", "who", "why", "with", "you", "about", "please",
    "does", "there", "this", "that",
}


def _clean_query(text: str) -> str:
    cleaned = re.sub(
        r"\b(mount\s*and\s*blade|mount&blade|bannerlord|warband|wiki|please|can you|could you|tell me|what is|what's)\b",
        " ",
        text,
        flags=re.I,
    )
    cleaned = re.sub(r"[^\w\s\-']", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text.strip()


def _extract_terms(query: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'\-]+", query.lower())
    terms = [w for w in words if len(w) > 2 and w not in STOPWORDS]
    return terms[:MAX_QUERY_TERMS]


def _strip_html_to_text(html: str) -> str:
    no_script = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    no_style = re.sub(r"<style[\s\S]*?</style>", " ", no_script, flags=re.I)
    no_tags = re.sub(r"<[^>]+>", " ", no_style)
    text = unescape(no_tags)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_wikitext_markup(text: str) -> str:
    text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"<ref[^>]*>[\s\S]*?</ref>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"''+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _search_wiki(query: str) -> dict | None:
    terms = _extract_terms(query)
    compact_query = " ".join(terms) if terms else query

    def _score_result(result: dict, domain: str) -> int:
        href = (result or {}).get("href") or (result or {}).get("url") or ""
        title = str((result or {}).get("title") or "")
        body = str((result or {}).get("body") or "")
        text = f"{title} {href} {body}".lower()

        score = 0
        if "/wiki/" in href:
            score += 25
        if "/wiki/category:" in href.lower() or title.lower().startswith("category:"):
            score -= 30
        if domain in href:
            score += 10

        for term in terms:
            if term in text:
                score += 8

        if "bannerlord" in text:
            score += 8
        if "warband" in text and "bannerlord" not in text:
            score -= 6
        return score

    def _search_via_wiki_api(domain: str) -> list[dict]:
        api_url = DOMAIN_API_ENDPOINTS.get(domain)
        if not api_url:
            return []
        try:
            resp = requests.get(
                api_url,
                timeout=SEARCH_TIMEOUT_SECONDS,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": compact_query,
                    "srlimit": 8,
                    "format": "json",
                },
                headers={"User-Agent": "Mitch/1.0 (+BannerlordWikiIntent)"},
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = ((payload or {}).get("query") or {}).get("search") or []
            out = []
            for row in rows:
                title = str((row or {}).get("title") or "").strip()
                if not title:
                    continue
                href = f"https://{domain}/wiki/{title.replace(' ', '_')}"
                snippet = _strip_html_to_text(str((row or {}).get("snippet") or ""))
                out.append({"title": title, "href": href, "body": snippet})
            return out
        except Exception as e:
            logger.warning(f"Bannerlord wiki API search failed ({domain}): {e}")
            return []

    for domain in SEARCH_DOMAINS:
        search_query = f"site:{domain} {compact_query}".strip()
        logger.info(f"Bannerlord wiki search query: {search_query}")

        api_candidates = _search_via_wiki_api(domain)
        if api_candidates:
            best = max(api_candidates, key=lambda r: _score_result(r, domain))
            if _score_result(best, domain) >= MIN_RESULT_SCORE:
                return best

        try:
            with DDGS() as ddgs:
                candidates = []
                for result in ddgs.text(search_query, max_results=12):
                    href = (result or {}).get("href") or (result or {}).get("url") or ""
                    if domain in href:
                        candidates.append(result)
                if not candidates:
                    continue
                best = max(candidates, key=lambda r: _score_result(r, domain))
                if _score_result(best, domain) >= MIN_RESULT_SCORE:
                    return best
        except Exception as e:
            logger.warning(f"Bannerlord wiki search failed ({domain}): {e}")
    return None


def _extract_page_title_from_url(url: str) -> str:
    try:
        marker = "/wiki/"
        idx = url.find(marker)
        if idx == -1:
            return ""
        slug = url[idx + len(marker):].split("?", 1)[0].split("#", 1)[0].strip()
        return unquote(slug)
    except Exception:
        return ""


def _get_api_endpoint(url: str) -> str | None:
    for domain, endpoint in DOMAIN_API_ENDPOINTS.items():
        if domain in (url or ""):
            return endpoint
    return None


def _fetch_wiki_excerpt_from_api(url: str) -> str:
    title = _extract_page_title_from_url(url)
    api_url = _get_api_endpoint(url)
    if not title or not api_url:
        return ""

    try:
        full_resp = requests.get(
            api_url,
            timeout=PAGE_TIMEOUT_SECONDS,
            params={
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json",
                "formatversion": "2",
            },
            headers={"User-Agent": "Mitch/1.0 (+BannerlordWikiIntent)"},
        )
        full_resp.raise_for_status()
        full_payload = full_resp.json()
        full_html = (((full_payload or {}).get("parse") or {}).get("text") or "")
        if full_html:
            text = _strip_html_to_text(full_html)
            if text:
                return text[:MAX_SNIPPET_CHARS]
    except Exception as e:
        logger.warning(f"Bannerlord wiki API text fetch failed for '{title}': {e}")

    try:
        raw_resp = requests.get(
            api_url,
            timeout=PAGE_TIMEOUT_SECONDS,
            params={
                "action": "parse",
                "page": title,
                "prop": "wikitext",
                "format": "json",
                "formatversion": "2",
            },
            headers={"User-Agent": "Mitch/1.0 (+BannerlordWikiIntent)"},
        )
        raw_resp.raise_for_status()
        raw_payload = raw_resp.json()
        wikitext = (((raw_payload or {}).get("parse") or {}).get("wikitext") or "")
        if wikitext:
            return _strip_wikitext_markup(wikitext[:MAX_SNIPPET_CHARS])[:MAX_SNIPPET_CHARS]
    except Exception as e:
        logger.warning(f"Bannerlord wiki API wikitext fallback failed for '{title}': {e}")

    return ""


def _extract_relevant_excerpt(text: str, query_terms: list[str]) -> str:
    if not text:
        return ""
    if not query_terms:
        return text[:MAX_SNIPPET_CHARS]

    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    scored = []
    for part in parts:
        lower = part.lower()
        score = sum(1 for term in query_terms if term in lower)
        if score > 0:
            scored.append((score, part))
    scored.sort(key=lambda item: item[0], reverse=True)

    selected = []
    total = 0
    for _, fragment in scored[:10]:
        fragment = fragment.strip()
        if not fragment:
            continue
        if total + len(fragment) + 1 > MAX_SNIPPET_CHARS:
            break
        selected.append(fragment)
        total += len(fragment) + 1

    if not selected:
        return text[:MAX_SNIPPET_CHARS]
    return " ".join(selected)[:MAX_SNIPPET_CHARS]


def _fetch_wiki_excerpt(url: str, query: str) -> str:
    api_excerpt = _fetch_wiki_excerpt_from_api(url)
    if api_excerpt:
        return api_excerpt[:MAX_SNIPPET_CHARS]

    try:
        resp = requests.get(
            url,
            timeout=PAGE_TIMEOUT_SECONDS,
            headers={"User-Agent": "Mitch/1.0 (+BannerlordWikiIntent)"},
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to fetch wiki page: {e}")
        return ""

    text = _strip_html_to_text(resp.text)
    terms = _extract_terms(query)
    return _extract_relevant_excerpt(text, terms)


def _emit_augmented_chat(prompt: str, context: str = "") -> None:
    payload = {"prompt": prompt, "force_openai_minimal": True, "request_type": "bannerlord_rag"}
    if context.strip():
        payload["retrieved_context"] = context
    event_bus.emit("EMIT_CHAT_REQUEST", payload)


def handle_bannerlord_wiki_query(data):
    if isinstance(data, dict):
        prompt = (data.get("prompt") or "").strip()
    elif isinstance(data, str):
        prompt = data.strip()
    else:
        prompt = ""
    if not prompt:
        return

    query = _clean_query(prompt)
    result = _search_wiki(query)
    if not result:
        logger.info("Bannerlord wiki: no result; continuing without retrieval.")
        _emit_augmented_chat(prompt)
        return

    url = result.get("href") or result.get("url") or ""
    title = result.get("title", "Bannerlord Wiki")
    if not url:
        logger.info("Bannerlord wiki: result missing URL; continuing without retrieval.")
        _emit_augmented_chat(prompt)
        return

    event_bus.emit("EMIT_OPEN_URL", {"url": url, "source": "bannerlord_wiki_intent"})

    excerpt = _fetch_wiki_excerpt(url, query)
    if not excerpt:
        body = (result.get("body") or "").strip()
        excerpt = body[:MAX_SNIPPET_CHARS]

    if not excerpt:
        logger.info("Bannerlord wiki: no usable excerpt; continuing without retrieval.")
        _emit_augmented_chat(prompt)
        return

    retrieved_context = (
        "Bannerlord wiki retrieval:\n"
        f"Source: {title}\n"
        f"URL: {url}\n"
        f"Excerpt: {excerpt}"
    )
    logger.info(
        f"Bannerlord wiki retrieval ok: url={url}, excerpt_chars={len(excerpt)}, prompt_chars={len(prompt)}"
    )
    _emit_augmented_chat(prompt, context=retrieved_context)


def _bannerlord_intent_handler(text: str):
    event_bus.emit(EVENT_NAME, {"prompt": text, "intent": "bannerlord_wiki_lookup"})


def start_module(event_bus):
    event_bus.subscribe(EVENT_NAME, handle_bannerlord_wiki_query)
    IntentRegistry.register_intent(
        name="bannerlord_wiki_lookup",
        handler=_bannerlord_intent_handler,
        keywords=[
            "bannerlord",
            "mount and blade",
            "mount & blade",
            "bannerlord wiki",
            "bannerlord companion",
            "bannerlord quest",
            "bannerlord smithing",
            "bannerlord workshop",
            "bannerlord clan",
        ],
        objects=[],
        priority=50,
    )
    logger.info("Bannerlord wiki intent module started.")
