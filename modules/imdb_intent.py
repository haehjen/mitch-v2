import json
import re
from html import unescape

import requests
from ddgs import DDGS

from core.event_bus import event_bus
from core.event_registry import IntentRegistry
from core.peterjones import get_logger

logger = get_logger("imdb_intent")

EVENT_NAME = "EMIT_IMDB_QUERY"
SEARCH_DOMAINS = ("www.imdb.com", "imdb.com", "m.imdb.com")
SEARCH_TIMEOUT_SECONDS = 10
PAGE_TIMEOUT_SECONDS = 10
MAX_SNIPPET_CHARS = 1800
MAX_QUERY_TERMS = 10
MIN_RESULT_SCORE = 24
USER_AGENT = "Mitch/1.0 (+IMDbIntent)"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "do", "for", "from", "how",
    "i", "in", "is", "it", "me", "of", "on", "or", "tell", "the", "to", "what",
    "when", "where", "which", "who", "why", "with", "you", "about", "please",
    "does", "there", "this", "that", "imdb", "movie", "movies", "film", "films",
    "show", "shows", "tv", "series", "actor", "actors", "actress", "actresses",
    "director", "directors", "cast", "episode", "episodes", "season", "seasons",
}

PERSON_CUES = {
    "actor", "actors", "actress", "actresses", "director", "directors",
    "writer", "writers", "producer", "producers", "star", "stars",
    "played", "plays", "portrayed", "portrays", "filmography",
}

TITLE_CUES = {
    "movie", "movies", "film", "films", "show", "shows", "tv", "series",
    "episode", "episodes", "season", "seasons", "plot", "rating",
}

NOISE_PATTERNS = [
    r"\bimdb\b",
    r"\bplease\b",
    r"\bcan you\b",
    r"\bcould you\b",
    r"\btell me\b",
    r"\bwhat is\b",
    r"\bwhat's\b",
    r"\bwho played\b",
    r"\bwho plays\b",
    r"\bwho starred in\b",
    r"\bwho stars in\b",
    r"\bwho is in\b",
    r"\bcast of\b",
    r"\bmovie\b",
    r"\bmovies\b",
    r"\bfilm\b",
    r"\bfilms\b",
    r"\btv show\b",
    r"\btv series\b",
    r"\bshow\b",
    r"\bshows\b",
    r"\bseries\b",
    r"\bactor\b",
    r"\bactors\b",
    r"\bactress\b",
    r"\bactresses\b",
    r"\bdirector\b",
    r"\bdirectors\b",
    r"\bcast\b",
    r"\bepisode\b",
    r"\bepisodes\b",
    r"\bseason\b",
    r"\bseasons\b",
    r"\brating\b",
    r"\bplot\b",
]


def _clean_query(text: str) -> str:
    cleaned = str(text or "")
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
    cleaned = re.sub(r"[^\w\s\-']", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or str(text or "").strip()


def _extract_terms(query: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'\-]+", query.lower())
    terms = [w for w in words if len(w) > 1 and w not in STOPWORDS]
    return terms[:MAX_QUERY_TERMS]


def _infer_target_kind(text: str) -> str:
    lowered = str(text or "").lower()
    person_hits = sum(1 for cue in PERSON_CUES if re.search(rf"\b{re.escape(cue)}\b", lowered))
    title_hits = sum(1 for cue in TITLE_CUES if re.search(rf"\b{re.escape(cue)}\b", lowered))
    if person_hits > title_hits:
        return "person"
    if title_hits > person_hits:
        return "title"
    return "unknown"


def _extract_result_url(result: dict) -> str:
    return str((result or {}).get("href") or (result or {}).get("url") or "").strip()


def _result_kind_from_url(url: str) -> str:
    lowered = str(url or "").lower()
    if "/name/" in lowered:
        return "person"
    if "/title/" in lowered:
        return "title"
    return "unknown"


def _score_result(result: dict, query_terms: list[str], preferred_kind: str) -> int:
    url = _extract_result_url(result)
    title = str((result or {}).get("title") or "")
    body = str((result or {}).get("body") or "")
    text = f"{title} {body} {url}".lower()
    result_kind = _result_kind_from_url(url)

    score = 0
    if any(domain in url for domain in SEARCH_DOMAINS):
        score += 12
    if "/title/" in url.lower() or "/name/" in url.lower():
        score += 24
    if preferred_kind != "unknown" and result_kind == preferred_kind:
        score += 16

    for term in query_terms:
        if term in text:
            score += 8

    if any(part in text for part in ("reviews", "review", "awards", "news", "photos", "video gallery")):
        score -= 10
    if "episode list" in text or "/episodes" in url.lower():
        score -= 6
    return score


def _search_imdb(query: str, original_prompt: str) -> dict | None:
    terms = _extract_terms(query)
    compact_query = " ".join(terms) if terms else query
    preferred_kind = _infer_target_kind(original_prompt)
    query_variants = []

    if preferred_kind == "person":
        query_variants.append(f"site:imdb.com/name/ {compact_query}".strip())
    elif preferred_kind == "title":
        query_variants.append(f"site:imdb.com/title/ {compact_query}".strip())

    query_variants.append(f"site:imdb.com {compact_query}".strip())

    try:
        with DDGS() as ddgs:
            best_result = None
            best_score = -1
            for search_query in query_variants:
                logger.info(f"IMDb search query: {search_query}")
                for result in ddgs.text(search_query, max_results=10):
                    result = result or {}
                    url = _extract_result_url(result)
                    if not any(domain in url for domain in SEARCH_DOMAINS):
                        continue
                    score = _score_result(result, terms, preferred_kind)
                    if score > best_score:
                        best_score = score
                        best_result = result
                if best_result and best_score >= MIN_RESULT_SCORE:
                    return best_result
            return best_result if best_score >= MIN_RESULT_SCORE else None
    except Exception as e:
        logger.warning(f"IMDb search failed: {e}")
        return None


def _strip_html_to_text(html: str) -> str:
    no_script = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    no_style = re.sub(r"<style[\s\S]*?</style>", " ", no_script, flags=re.I)
    no_tags = re.sub(r"<[^>]+>", " ", no_style)
    text = unescape(no_tags)
    return re.sub(r"\s+", " ", text).strip()


def _extract_meta_content(html: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+name="{re.escape(key)}"[^>]+content="([^"]+)"',
        rf'<meta[^>]+property="{re.escape(key)}"[^>]+content="([^"]+)"',
        rf'<meta[^>]+content="([^"]+)"[^>]+name="{re.escape(key)}"',
        rf'<meta[^>]+content="([^"]+)"[^>]+property="{re.escape(key)}"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            return unescape(match.group(1)).strip()
    return ""


def _extract_json_ld_objects(html: str) -> list[dict]:
    objects: list[dict] = []
    for raw in re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>([\s\S]*?)</script>',
        html,
        flags=re.I,
    ):
        payload = raw.strip()
        if not payload:
            continue
        try:
            decoded = json.loads(unescape(payload))
        except Exception:
            continue
        if isinstance(decoded, list):
            objects.extend(item for item in decoded if isinstance(item, dict))
        elif isinstance(decoded, dict):
            if isinstance(decoded.get("@graph"), list):
                objects.extend(item for item in decoded["@graph"] if isinstance(item, dict))
            else:
                objects.append(decoded)
    return objects


def _pick_primary_json_ld(objects: list[dict], url: str) -> dict:
    target_kind = _result_kind_from_url(url)
    preferred_types = (
        {"Person"} if target_kind == "person"
        else {"Movie", "TVSeries", "TVEpisode", "TVSeason", "CreativeWorkSeries"}
    )

    for obj in objects:
        obj_type = obj.get("@type")
        if isinstance(obj_type, list):
            type_names = {str(item) for item in obj_type}
        else:
            type_names = {str(obj_type)} if obj_type else set()
        if type_names & preferred_types:
            return obj

    for obj in objects:
        if obj.get("name") or obj.get("description"):
            return obj
    return {}


def _collect_names(value, max_items: int = 6) -> list[str]:
    if not value:
        return []
    items = value if isinstance(value, list) else [value]
    names = []
    for item in items:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            names.append(name)
        if len(names) >= max_items:
            break
    return names


def _compose_title_excerpt(data: dict, html: str) -> str:
    parts = []

    title = str(data.get("name") or "").strip()
    type_name = data.get("@type")
    if isinstance(type_name, list):
        type_name = next((item for item in type_name if item), "")
    rating = data.get("aggregateRating") or {}
    rating_value = str((rating or {}).get("ratingValue") or "").strip()
    rating_count = str((rating or {}).get("ratingCount") or "").strip()
    published = str(data.get("datePublished") or "").strip()
    genres = _collect_names(data.get("genre"), max_items=4)
    cast = _collect_names(data.get("actor"), max_items=6)
    directors = _collect_names(data.get("director"), max_items=4)
    creators = _collect_names(data.get("creator"), max_items=4)
    description = str(data.get("description") or "").strip()
    meta_description = _extract_meta_content(html, "description")

    if title:
        label_bits = [str(type_name or "").strip(), published[:4] if published else ""]
        label = ", ".join(bit for bit in label_bits if bit)
        parts.append(f"Title: {title}" + (f" ({label})" if label else ""))
    if rating_value:
        rating_text = f"IMDb rating: {rating_value}/10"
        if rating_count:
            rating_text += f" from {rating_count} votes"
        parts.append(rating_text)
    if genres:
        parts.append(f"Genres: {', '.join(genres)}")
    if cast:
        parts.append(f"Cast: {', '.join(cast)}")
    if directors:
        parts.append(f"Directors: {', '.join(directors)}")
    elif creators:
        parts.append(f"Creators: {', '.join(creators)}")
    if description:
        parts.append(f"Summary: {description}")
    elif meta_description:
        parts.append(f"Summary: {meta_description}")

    return " | ".join(part for part in parts if part)[:MAX_SNIPPET_CHARS]


def _compose_person_excerpt(data: dict, html: str) -> str:
    parts = []

    name = str(data.get("name") or "").strip()
    description = str(data.get("description") or "").strip()
    meta_description = _extract_meta_content(html, "description")
    meta_title = _extract_meta_content(html, "og:title")
    known_for = _collect_names(data.get("knowsAbout"), max_items=5)
    same_as = _collect_names(data.get("sameAs"), max_items=4)

    if name:
        parts.append(f"Person: {name}")
    if meta_title and meta_title != name:
        parts.append(f"IMDb page: {meta_title}")
    if description:
        parts.append(f"Bio: {description}")
    elif meta_description:
        parts.append(f"Bio: {meta_description}")
    if known_for:
        parts.append(f"Known for: {', '.join(known_for)}")
    if same_as:
        parts.append(f"Links: {', '.join(same_as)}")

    return " | ".join(part for part in parts if part)[:MAX_SNIPPET_CHARS]


def _extract_relevant_excerpt(text: str, query_terms: list[str]) -> str:
    if not text:
        return ""
    if not query_terms:
        return text[:MAX_SNIPPET_CHARS]

    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    scored = []
    for part in parts:
        lowered = part.lower()
        score = sum(1 for term in query_terms if term in lowered)
        if score > 0:
            scored.append((score, part))
    scored.sort(key=lambda item: item[0], reverse=True)

    selected = []
    total = 0
    for _, fragment in scored[:8]:
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


def _fetch_imdb_excerpt(url: str, query: str) -> str:
    try:
        resp = requests.get(
            url,
            timeout=PAGE_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to fetch IMDb page: {e}")
        return ""

    html = resp.text or ""
    json_ld_objects = _extract_json_ld_objects(html)
    primary = _pick_primary_json_ld(json_ld_objects, url)

    if primary:
        kind = _result_kind_from_url(url)
        if kind == "person":
            excerpt = _compose_person_excerpt(primary, html)
        else:
            excerpt = _compose_title_excerpt(primary, html)
        if excerpt:
            return excerpt[:MAX_SNIPPET_CHARS]

    meta_description = _extract_meta_content(html, "description")
    if meta_description:
        return meta_description[:MAX_SNIPPET_CHARS]

    text = _strip_html_to_text(html)
    terms = _extract_terms(query)
    return _extract_relevant_excerpt(text, terms)


def _emit_augmented_chat(prompt: str, context: str = "") -> None:
    payload = {"prompt": prompt, "force_openai_minimal": True, "request_type": "imdb_rag"}
    if context.strip():
        payload["retrieved_context"] = context
    event_bus.emit("EMIT_CHAT_REQUEST", payload)


def handle_imdb_query(data):
    if isinstance(data, dict):
        prompt = (data.get("prompt") or "").strip()
    elif isinstance(data, str):
        prompt = data.strip()
    else:
        prompt = ""
    if not prompt:
        return

    query = _clean_query(prompt)
    result = _search_imdb(query, prompt)
    if not result:
        logger.info("IMDb: no result; continuing without retrieval.")
        _emit_augmented_chat(prompt)
        return

    url = _extract_result_url(result)
    title = str((result or {}).get("title") or "IMDb").strip() or "IMDb"
    if not url:
        logger.info("IMDb: result missing URL; continuing without retrieval.")
        _emit_augmented_chat(prompt)
        return

    event_bus.emit("EMIT_OPEN_URL", {"url": url, "source": "imdb_intent"})

    excerpt = _fetch_imdb_excerpt(url, query)
    if not excerpt:
        body = str((result or {}).get("body") or "").strip()
        excerpt = body[:MAX_SNIPPET_CHARS]

    if not excerpt:
        logger.info("IMDb: no usable excerpt; continuing without retrieval.")
        _emit_augmented_chat(prompt)
        return

    retrieved_context = (
        "IMDb retrieval:\n"
        f"Source: {title}\n"
        f"URL: {url}\n"
        f"Excerpt: {excerpt}"
    )
    logger.info(
        f"IMDb retrieval ok: url={url}, excerpt_chars={len(excerpt)}, prompt_chars={len(prompt)}"
    )
    _emit_augmented_chat(prompt, context=retrieved_context)


def _imdb_intent_handler(text: str):
    event_bus.emit(EVENT_NAME, {"prompt": text, "intent": "imdb_lookup"})


def start_module(event_bus):
    event_bus.subscribe(EVENT_NAME, handle_imdb_query)
    IntentRegistry.register_intent(
        name="imdb_lookup",
        handler=_imdb_intent_handler,
        keywords=[
            "imdb",
            "movie",
            "movies",
            "film",
            "films",
            "tv show",
            "tv series",
            "series",
            "actor",
            "actors",
            "actress",
            "director",
            "cast",
            "episode",
            "season",
            "movie cast",
            "show cast",
            "cast of",
            "who played",
            "who plays",
            "who starred in",
            "who stars in",
            "actor in",
            "director of",
            "movie rating",
            "episode rating",
        ],
        objects=[],
        priority=0,
    )
    logger.info("IMDb intent module started.")
