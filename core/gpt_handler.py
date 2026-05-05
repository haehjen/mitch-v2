import threading
import json
import re
import time
from openai import OpenAI
from pathlib import Path
import os
from core.event_bus import event_bus
from core.peterjones import get_logger
from core import memory, persona
from core.config import MITCH_ROOT
import requests

PRIMARY_ENGINE = os.getenv("MITCH_PRIMARY_ENGINE", "ollama").lower()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.4.251:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")

OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "160"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
OLLAMA_MAX_DURATION = float(os.getenv("OLLAMA_MAX_DURATION_SECONDS", str(max(180, int(OLLAMA_TIMEOUT * 2)))))
OLLAMA_PROMPT_MAX_CHARS = int(
    os.getenv("OLLAMA_PROMPT_MAX_CHARS", str(max(4000, OLLAMA_NUM_CTX * 3)))
)
OLLAMA_STREAM = os.getenv("OLLAMA_STREAM", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}
OLLAMA_MEMORY_WINDOW = int(os.getenv("OLLAMA_MEMORY_WINDOW", "4"))
OLLAMA_MAX_INJECTION_ITEMS = int(os.getenv("OLLAMA_MAX_INJECTION_ITEMS", "20"))
OLLAMA_INJECTION_ITEM_MAX_CHARS = int(os.getenv("OLLAMA_INJECTION_ITEM_MAX_CHARS", "400"))
OLLAMA_INJECTION_TOTAL_MAX_CHARS = int(os.getenv("OLLAMA_INJECTION_TOTAL_MAX_CHARS", "2500"))
OLLAMA_EXCLUDED_INJECTIONS = {
    part.strip()
    for part in os.getenv("OLLAMA_EXCLUDED_INJECTIONS", "event_registry,protest_data").split(",")
    if part.strip()
}
OLLAMA_RAG_MEMORY_WINDOW = int(os.getenv("OLLAMA_RAG_MEMORY_WINDOW", "1"))

OPENAI_MAX_INJECTION_ITEMS = int(os.getenv("OPENAI_MAX_INJECTION_ITEMS", "8"))
OPENAI_INJECTION_ITEM_MAX_CHARS = int(os.getenv("OPENAI_INJECTION_ITEM_MAX_CHARS", "220"))
OPENAI_INJECTION_TOTAL_MAX_CHARS = int(os.getenv("OPENAI_INJECTION_TOTAL_MAX_CHARS", "1200"))
OPENAI_EXCLUDED_INJECTIONS = {
    part.strip()
    for part in os.getenv(
        "OPENAI_EXCLUDED_INJECTIONS",
        (
            "event_registry,protest_data,aggregated_context,contextual_event_summaries,"
            "activity_recommendation,conversation_enhancements,time_suggestion,"
            "event_predictions,user_engagement,event_insights,reflective_analysis,"
            "insight_aggregator,contextual_insights,contextual_protest_analysis"
        ),
    ).split(",")
    if part.strip()
}
OPENAI_ALLOWED_INJECTIONS = {
    part.strip()
    for part in os.getenv(
        "OPENAI_ALLOWED_INJECTIONS",
        (
            "knowledge_injection,contextual_focus,focus_injection,personalization_injection,"
            "contextual_intent,contextual_intent_enhancer,contextual_skill_enhancer,"
            "contextual_event_analysis,contextual_intelligence"
        ),
    ).split(",")
    if part.strip()
}

logger = get_logger("gptv2")

if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY not found; GPT features will fail unless set.")

client = None

OPENAI_MODEL = "gpt-4o"
MEMORY_WINDOW = 8
INJECTION_PATH = Path(MITCH_ROOT) / "data" / "injections"
PROMPT_DEBUG_LOG = Path(MITCH_ROOT) / "logs" / "gpt_prompt_debug.txt"

active_token = None


def _normalize_openai_history(recent):
    """
    OpenAI Chat Completions only accepts tool-role messages when paired with
    prior assistant tool_calls. Our memory store is flat and may contain
    arbitrary roles (e.g. "tool"), so normalize unknown roles into user text.
    """
    normalized = []
    for entry in recent or []:
        role = str(entry.get("role", "user") or "user").strip().lower()
        content = str(entry.get("content", "") or "")
        if role in {"user", "assistant"}:
            normalized.append({"role": role, "content": content})
            continue
        normalized.append(
            {
                "role": "user",
                "content": f"[memory:{role}] {content}",
            }
        )
    return normalized


def _emit_contextual_chat_events(stage: str, text: str, token: str, extra: dict | None = None):
    """
    Bridge normal chat flow into contextual module event streams.
    This makes contextual modules useful during routine conversations.
    """
    payload = {
        "stage": stage,
        "text": text or "",
        "token": token,
        "source": "chat",
    }
    if extra and isinstance(extra, dict):
        payload.update(extra)

    try:
        event_bus.emit("USER_ACTIVITY", payload)

        if stage == "user_input":
            event_bus.emit(
                "CONVERSATION_EVENT",
                {"role": "user", "text": text or "", "token": token, "source": "chat"},
            )
            event_bus.emit("USER_INTENT", {"text": text or "", "token": token, "source": "chat"})
            event_bus.emit(
                "INTENT_ANALYSIS_REQUEST",
                {"text": text or "", "token": token, "source": "chat"},
            )
        elif stage == "assistant_output":
            event_bus.emit(
                "CONVERSATION_EVENT",
                {"role": "assistant", "text": text or "", "token": token, "source": "chat"},
            )
    except Exception as e:
        logger.warning(f"Failed emitting contextual chat events ({stage}): {e}")


def load_prompt_injections(
    excluded_modules=None,
    allowed_modules=None,
    max_items=None,
    item_max_chars=None,
    total_max_chars=None,
    exclude_prefixes=None,
):
    if not INJECTION_PATH.exists():
        return []
    excluded_modules = excluded_modules or set()
    exclude_prefixes = tuple(exclude_prefixes or ())
    lines = []
    total_chars = 0
    for file in sorted(INJECTION_PATH.glob("*.json")):
        if allowed_modules is not None and file.stem not in allowed_modules:
            continue
        if file.stem in excluded_modules:
            continue
        if exclude_prefixes and any(file.stem.startswith(prefix) for prefix in exclude_prefixes):
            continue
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
            items = raw if isinstance(raw, list) else [raw]
            for entry in items:
                module = file.stem
                if isinstance(entry, dict):
                    type_ = entry.get("type", "misc")
                    content = entry.get("content", entry)
                else:
                    type_ = "misc"
                    content = entry

                if isinstance(content, str):
                    safe_content = content
                else:
                    safe_content = json.dumps(content, ensure_ascii=False)

                safe_content = safe_content.encode("utf-8", errors="replace").decode("utf-8")
                if item_max_chars and len(safe_content) > item_max_chars:
                    safe_content = safe_content[:item_max_chars] + "..."
                if safe_content:
                    lines.append(f"- [{module}/{type_}] {safe_content}")
                    total_chars += len(safe_content)
                    if total_max_chars and total_chars >= total_max_chars:
                        lines.append("- [context/misc] Additional injections omitted for size.")
                        return lines
                    if max_items and len(lines) >= max_items:
                        lines.append("- [context/misc] Additional injections omitted for size.")
                        return lines
        except Exception as e:
            logger.warning(f"Skipping malformed injection file {file.name}: {e}")
    return lines


def build_system_prompt(
    excluded_modules=None,
    allowed_modules=None,
    max_injection_items=None,
    injection_item_max_chars=None,
    injection_total_max_chars=None,
    injection_exclude_prefixes=None,
):
    base = persona.build_system_prompt()
    injections = load_prompt_injections(
        excluded_modules=excluded_modules,
        allowed_modules=allowed_modules,
        max_items=max_injection_items,
        item_max_chars=injection_item_max_chars,
        total_max_chars=injection_total_max_chars,
        exclude_prefixes=injection_exclude_prefixes,
    )
    if injections:
        return f"{base}\n\n\U0001F527 Active Prompt Injections:\n" + "\n".join(injections)
    return base


def generate_token():
    import time

    return str(time.time()).replace(".", "")


def emit_chunk(chunk, token):
    # Avoid sending fenced code ticks as individual chunks (can break some UIs)
    if chunk.strip().startswith("```"):
        return
    event_bus.emit("EMIT_SPEAK_CHUNK", {"chunk": chunk, "token": token})


def emit_end(token, full_text=None):
    payload = {"token": token}
    if full_text is not None:
        payload["full_text"] = full_text
    event_bus.emit("EMIT_SPEAK_END", payload)


def emit_token_registered(token):
    event_bus.emit("EMIT_TOKEN_REGISTERED", {"token": token})
    event_bus.emit("EMIT_VISUAL_TOKEN", {"token": token})


def maybe_emit_module_create(response_text):
    code_match = re.search(r"```(?:python)?\n(.*?)```", response_text, re.DOTALL)
    file_match = re.search(r"`?(\w+\.py)`?", response_text)
    if code_match and file_match:
        filename = f"modules/{file_match.group(1)}"
        code = code_match.group(1).strip()
        logger.info(f"Detected module creation: {filename}")
        event_bus.emit(
            "EMIT_MODULE_CREATE",
            {
                "filename": filename,
                "code": code,
            },
        )


def handle_chat_request(data):
    """
    Entry point for user chat. IMPORTANT: we no longer save the user prompt here.
    Saving here caused duplication because recall() would include the just-saved
    prompt and stream_from_openai() would append it again.
    """
    global active_token
    if not isinstance(data, dict):
        data = {"prompt": str(data or "")}
    prompt = data.get("prompt", "")
    retrieved_context = data.get("retrieved_context", "")
    force_openai_minimal = bool(data.get("force_openai_minimal"))
    request_type = data.get("request_type")
    supplied_token = str(data.get("token", "") or "").strip()
    token = supplied_token or generate_token()
    active_token = token
    emit_token_registered(token)
    logger.info(f"New chat request: {prompt} (token: {token})")
    _emit_contextual_chat_events(
        "user_input",
        prompt,
        token,
        {
            "request_type": request_type,
            "force_openai_minimal": force_openai_minimal,
        },
    )

    try:
        if force_openai_minimal:
            thread = threading.Thread(
                target=stream_from_openai_minimal_rag,
                args=(prompt, token, retrieved_context, request_type),
            )
        elif PRIMARY_ENGINE == "openai":
            thread = threading.Thread(
                target=stream_from_openai,
                args=(prompt, token, True, retrieved_context),
            )
        else:
            thread = threading.Thread(
                target=stream_from_ollama_http,
                args=(prompt, token, True, retrieved_context),
            )
        thread.start()
    except Exception as e:
        logger.error(f"Chat thread start failed: {e}")
        fallback_or_fail(prompt, token, retrieved_context=retrieved_context)


def _get_openai_client():
    global client
    if client is None:
        client = OpenAI()
    return client


def _log_prompt_debug(engine: str, payload: dict):
    try:
        PROMPT_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with PROMPT_DEBUG_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {engine.upper()} PROMPT ===\n")
            f.write(json.dumps(payload, indent=2, ensure_ascii=False))
            f.write("\n")
    except Exception as e:
        logger.warning(f"Failed to write prompt debug log: {e}")


def _compute_system_prompt_parts(system_prompt: str):
    marker = "\n\n🔧 Active Prompt Injections:\n"
    if marker in system_prompt:
        base, injected = system_prompt.split(marker, 1)
        return len(base), len(injected)
    return len(system_prompt), 0


def _emit_token_diagnostics(token: str, engine: str, data: dict):
    payload = {"token": token, "engine": engine}
    payload.update(data or {})
    event_bus.emit("EMIT_TOKEN_DIAGNOSTICS", payload)


def _build_context_blocks(prompt: str, for_ollama: bool = False, retrieved_context: str = ""):
    if for_ollama:
        system_prompt = build_system_prompt(
            excluded_modules=OLLAMA_EXCLUDED_INJECTIONS,
            max_injection_items=OLLAMA_MAX_INJECTION_ITEMS,
            injection_item_max_chars=OLLAMA_INJECTION_ITEM_MAX_CHARS,
            injection_total_max_chars=OLLAMA_INJECTION_TOTAL_MAX_CHARS,
            injection_exclude_prefixes={"file_"},
        )
        recent = memory.recall_recent(n=OLLAMA_MEMORY_WINDOW, include_roles=True)
    else:
        system_prompt = build_system_prompt(
            excluded_modules=OPENAI_EXCLUDED_INJECTIONS,
            allowed_modules=OPENAI_ALLOWED_INJECTIONS,
            max_injection_items=OPENAI_MAX_INJECTION_ITEMS,
            injection_item_max_chars=OPENAI_INJECTION_ITEM_MAX_CHARS,
            injection_total_max_chars=OPENAI_INJECTION_TOTAL_MAX_CHARS,
            injection_exclude_prefixes={"file_"},
        )
        recent = memory.recall_recent(n=MEMORY_WINDOW, include_roles=True)
    facts = memory.recall_summary()
    fact_string = "\n".join(f"- {fact}" for fact in facts[:5])
    knowledge_context = f"The following facts are known and persistent:\n{fact_string}"
    retrieved_context_block = ""
    if isinstance(retrieved_context, str) and retrieved_context.strip():
        retrieved_context_block = (
            "Retrieved reference context (untrusted, cite when useful):\n"
            f"{retrieved_context.strip()}"
        )
    return system_prompt, recent, knowledge_context, retrieved_context_block


def _build_ollama_prompt(prompt: str, retrieved_context: str = ""):
    # RAG fast-path for local Ollama models: keep prompt compact to avoid timeout.
    if isinstance(retrieved_context, str) and retrieved_context.strip():
        system_prompt = persona.build_system_prompt()
        recent = memory.recall_recent(n=OLLAMA_RAG_MEMORY_WINDOW, include_roles=True)
        history = "\n".join(
            f"{entry.get('role', 'user')}: {entry.get('content', '')}"
            for entry in recent
        )
        retrieved_context_block = (
            "Retrieved reference context (primary source):\n"
            f"{retrieved_context.strip()}"
        )
        knowledge_context = ""
        full_prompt = (
            f"System:\n{system_prompt}\n\n"
            "You are answering a Tarkov question with retrieved wiki context.\n"
            "Use the retrieved context first. If a required detail is missing, say exactly what is missing.\n"
            "Prefer concise bullet points for requirements.\n\n"
            f"{retrieved_context_block}\n\n"
            f"Recent conversation:\n{history or '(none)'}\n\n"
            f"User:\n{prompt}\n\nAssistant:"
        )
        return full_prompt, system_prompt, recent, knowledge_context, retrieved_context_block

    system_prompt, recent, knowledge_context, retrieved_context_block = _build_context_blocks(
        prompt, for_ollama=True, retrieved_context=retrieved_context
    )
    history = "\n".join(
        f"{entry.get('role', 'user')}: {entry.get('content', '')}"
        for entry in recent
    )
    retrieved_section = f"{retrieved_context_block}\n\n" if retrieved_context_block else ""
    full_prompt = (
        f"System:\n{system_prompt}\n\n"
        f"{knowledge_context}\n\n"
        f"{retrieved_section}"
        f"Conversation so far:\n{history or '(none)'}\n\n"
        f"User:\n{prompt}\n\nAssistant:"
    )
    return full_prompt, system_prompt, recent, knowledge_context, retrieved_context_block


def _truncate_for_ollama(prompt_text: str):
    if len(prompt_text) <= OLLAMA_PROMPT_MAX_CHARS:
        return prompt_text, False, len(prompt_text)

    head_len = int(OLLAMA_PROMPT_MAX_CHARS * 0.65)
    marker = "\n\n[...prompt truncated for ollama context limit...]\n\n"
    tail_len = max(0, OLLAMA_PROMPT_MAX_CHARS - head_len - len(marker))
    truncated = prompt_text[:head_len] + marker + prompt_text[-tail_len:]
    return truncated, True, len(prompt_text)


def stream_from_openai(prompt, token, allow_fallback=True, retrieved_context=""):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")
        system_prompt, recent, knowledge_context, retrieved_context_block = _build_context_blocks(
            prompt, retrieved_context=retrieved_context
        )
        user_content = prompt
        if retrieved_context_block:
            user_content = (
                f"{prompt}\n\n"
                f"{retrieved_context_block}\n\n"
                "Use this context only if relevant and accurate."
            )
        history_chars = sum(len(str(entry.get("content", ""))) for entry in recent)
        system_base_chars, injection_chars = _compute_system_prompt_parts(system_prompt)
        prompt_total_chars = (
            system_base_chars
            + injection_chars
            + len(knowledge_context)
            + history_chars
            + len(user_content)
        )

        normalized_recent = _normalize_openai_history(recent)

        # Construct messages payload
        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n{knowledge_context}"},
            *normalized_recent,
            {"role": "user", "content": user_content},
        ]
        _log_prompt_debug(
            "openai",
            {
                "token": token,
                "model": OPENAI_MODEL,
                "temperature": 0.7,
                "messages": messages,
                "retrieved_context_chars": len(retrieved_context_block or ""),
            },
        )

        # Ensure the client and parameters are valid
        response = _get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,  # Ensure OPENAI_MODEL is a valid string
            messages=messages,  # Ensure messages is a list of dicts with "role" and "content"
            temperature=0.7,  # Ensure temperature is a float
            stream=True,  # Ensure stream is a boolean
        )

        response_buffer = ""
        for chunk in response:
            part = chunk.choices[0].delta.content
            if part:
                response_buffer += part
                emit_chunk(part, token)

        emit_end(token, response_buffer)

        # Persist AFTER completion to avoid duplicate user message in recall()
        memory.save_memory("user", prompt)
        memory.save_memory("assistant", response_buffer)
        _emit_contextual_chat_events("assistant_output", response_buffer, token, {"engine": "openai"})
        _emit_token_diagnostics(
            token,
            "openai",
            {
                "system_base_chars": system_base_chars,
                "injection_chars": injection_chars,
                "knowledge_chars": len(knowledge_context),
                "history_chars": history_chars,
                "user_chars": len(user_content),
                "retrieved_chars": len(retrieved_context_block or ""),
                "prompt_total_chars": prompt_total_chars,
                "response_chars": len(response_buffer),
            },
        )

        maybe_emit_module_create(response_buffer)

    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        if allow_fallback:
            fallback_or_fail(prompt, token, retrieved_context=retrieved_context)
        else:
            emit_chunk("Both local and fallback failed.", token)
            emit_end(token)


def stream_from_openai_minimal_rag(prompt, token, retrieved_context="", request_type=None):
    topic_label = (
        "Tarkov" if request_type == "tarkov_rag"
        else "Pokemon" if request_type == "pokemon_rag"
        else "Bannerlord" if request_type == "bannerlord_rag"
        else "IMDb" if request_type == "imdb_rag"
        else "NSSR" if request_type == "nssr_rag"
        else "wiki"
    )
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        source_block = (retrieved_context or "").strip()
        # Keep persona continuity even in minimal RAG paths.
        # This also enforces persona hash verification via persona.build_system_prompt().
        persona_system = persona.build_system_prompt()
        messages = [
            {
                "role": "system",
                "content": (
                    f"{persona_system}\n\n"
                    f"You are answering a {topic_label} lookup with source text. "
                    "Use the provided source text first. "
                    "Return a concise, practical answer in plain language with bullet points where useful. "
                    "If a required detail is missing from source text, say exactly what is missing."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{prompt}\n\n"
                    f"Source text:\n{source_block or '(no source text provided)'}"
                ),
            },
        ]
        _log_prompt_debug(
            f"openai_{topic_label.lower()}_minimal",
            {
                "token": token,
                "model": OPENAI_MODEL,
                "messages": messages,
                "source_chars": len(source_block),
                "request_type": request_type,
            },
        )

        response = _get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.2,
            stream=True,
        )

        response_buffer = ""
        for chunk in response:
            part = chunk.choices[0].delta.content
            if part:
                response_buffer += part
                emit_chunk(part, token)

        emit_end(token, response_buffer)
        memory.save_memory("user", prompt)
        memory.save_memory("assistant", response_buffer)
        _emit_contextual_chat_events(
            "assistant_output",
            response_buffer,
            token,
            {"engine": "openai_minimal_rag"},
        )
        user_content = messages[-1].get("content", "")
        _emit_token_diagnostics(
            token,
            "openai_minimal_rag",
            {
                "system_base_chars": len(messages[0].get("content", "")),
                "injection_chars": 0,
                "knowledge_chars": 0,
                "history_chars": 0,
                "user_chars": len(user_content),
                "retrieved_chars": len(source_block),
                "prompt_total_chars": len(messages[0].get("content", "")) + len(user_content),
                "response_chars": len(response_buffer),
            },
        )
    except Exception as e:
        logger.error(f"OpenAI minimal {topic_label} error: {e}")
        emit_chunk(f"{topic_label} lookup is available but OpenAI response failed.", token)
        emit_end(token, response_buffer)


def stream_from_ollama_http(prompt, token, allow_fallback=True, retrieved_context=""):
    try:
        started = time.time()
        (
            full_prompt,
            system_prompt,
            recent,
            knowledge_context,
            retrieved_context_block,
        ) = _build_ollama_prompt(prompt, retrieved_context=retrieved_context)
        history_chars = sum(len(str(entry.get("content", ""))) for entry in recent)
        system_base_chars, injection_chars = _compute_system_prompt_parts(system_prompt)
        prompt_total_chars = (
            system_base_chars
            + injection_chars
            + len(knowledge_context)
            + history_chars
            + len(prompt)
            + len(retrieved_context_block or "")
        )
        ollama_prompt, was_truncated, original_len = _truncate_for_ollama(full_prompt)
        if was_truncated:
            logger.warning(
                f"Ollama prompt truncated for token {token}: {original_len} -> {len(ollama_prompt)} chars."
            )

        ollama_payload = {
            "model": OLLAMA_MODEL,
            "prompt": ollama_prompt,
            "stream": OLLAMA_STREAM,
            "options": {
                "num_ctx": OLLAMA_NUM_CTX,
                "num_predict": OLLAMA_NUM_PREDICT,
                "temperature": OLLAMA_TEMPERATURE,
            },
        }
        _log_prompt_debug(
            "ollama",
            {
                "token": token,
                "url": f"{OLLAMA_BASE_URL}/api/generate",
                "prompt_truncated": was_truncated,
                "prompt_original_chars": original_len,
                "prompt_final_chars": len(ollama_prompt),
                "system_prompt": system_prompt,
                "recent": recent,
                "knowledge_context": knowledge_context,
                "retrieved_context": retrieved_context_block,
                **ollama_payload,
            },
        )
        logger.info(f"Ollama full prompt (token: {token}): {ollama_prompt}")
        logger.info(
            f"Ollama request start (token: {token}, model: {OLLAMA_MODEL}, stream: {OLLAMA_STREAM}, timeout: {OLLAMA_TIMEOUT}s)."
        )

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            headers={"Content-Type": "application/json"},
            data=json.dumps(ollama_payload),
            timeout=(10, OLLAMA_TIMEOUT),
            stream=OLLAMA_STREAM,
        )

        response.raise_for_status()
        text = ""
        if OLLAMA_STREAM:
            loop_started = time.time()
            for raw_line in response.iter_lines(decode_unicode=True):
                if time.time() - loop_started > OLLAMA_MAX_DURATION:
                    raise TimeoutError(
                        f"Ollama stream exceeded max duration ({OLLAMA_MAX_DURATION}s)."
                    )
                if not raw_line:
                    continue
                try:
                    payload = json.loads(raw_line)
                except Exception:
                    logger.warning(f"Ollama stream parse error (token: {token}): {raw_line[:160]}")
                    continue
                part = payload.get("response", "")
                if part:
                    text += part
                    emit_chunk(part, token)
            if not text.strip():
                raise RuntimeError("Ollama returned empty streamed response.")
        else:
            data = response.json()
            text = data.get("response", "")
            if not text.strip():
                raise RuntimeError("Ollama returned empty response.")
            emit_chunk(text, token)

        emit_end(token)
        logger.info(f"Ollama request done (token: {token}) in {time.time() - started:.2f}s.")

        memory.save_memory("user", prompt)
        memory.save_memory("assistant", text)
        _emit_contextual_chat_events("assistant_output", text, token, {"engine": "ollama"})
        _emit_token_diagnostics(
            token,
            "ollama",
            {
                "system_base_chars": system_base_chars,
                "injection_chars": injection_chars,
                "knowledge_chars": len(knowledge_context),
                "history_chars": history_chars,
                "user_chars": len(prompt),
                "retrieved_chars": len(retrieved_context_block or ""),
                "prompt_total_chars": prompt_total_chars,
                "response_chars": len(text),
                "truncated": bool(was_truncated),
            },
        )

    except Exception as e:
        logger.error(f"Ollama request error: {e}")
        if allow_fallback:
            fallback_or_fail(prompt, token, retrieved_context=retrieved_context)
        else:
            emit_chunk("Both local and fallback failed.", token)
            emit_end(token, "Both local and fallback failed.")

def handle_module_request(data):
    prompt = data.get("prompt", "")
    token = generate_token()
    emit_token_registered(token)
    logger.info(f"Module request: {prompt} (token: {token})")

    engineer_prompt = (
        "You are a senior Python software engineer. "
        "Your task is to write a complete Python script based on the following request. "
        "Reply ONLY with a valid Python code block. "
        "Do not include any explanation, commentary, or formatting outside the code.\n\n"
        f"Request:\n{prompt}"
    )

    messages = [
        {"role": "system", "content": engineer_prompt},
    ]

    try:
        response = _get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,  # Ensure OPENAI_MODEL is a valid string
            messages=messages,  # Ensure messages is a list of dicts with "role" and "content"
            temperature=0.7,  # Ensure temperature is a float
            stream=False,  # Ensure stream is a boolean
        )

        if not response.choices:
            raise ValueError("Empty choices in GPT response")

        full_response = response.choices[0].message.content
        memory.save_memory("assistant", full_response)
        maybe_emit_module_create(full_response)
        emit_chunk(full_response, token)
        emit_end(token, f"{topic_label} lookup is available but OpenAI response failed.")

    except Exception as e:
        logger.error(f"Module generation failed: {e}")
        fallback_or_fail(prompt, token)


def fallback_or_fail(prompt, token, retrieved_context=""):
    if PRIMARY_ENGINE == "ollama":
        logger.warning("Ollama failed, falling back to OpenAI.")
        try:
            stream_from_openai(
                prompt,
                token,
                allow_fallback=False,
                retrieved_context=retrieved_context,
            )
        except Exception as e:
            logger.error(f"OpenAI fallback failed: {e}")
            emit_chunk("Both local and fallback failed.", token)
            emit_end(token)
    else:
        logger.warning("OpenAI failed, falling back to Ollama.")
        try:
            stream_from_ollama_http(
                prompt,
                token,
                allow_fallback=False,
                retrieved_context=retrieved_context,
            )
        except Exception as e:
            logger.error(f"Ollama fallback failed: {e}")
            emit_chunk("Something went wrong.", token)
            emit_end(token)

def on_chat_request(data):
    handle_chat_request(data)


def on_module_request(data):
    handle_module_request(data)


def _build_tool_narration_prompt(tool_name: str, output: str):
    return (
        "A backend tool just returned data. Respond as Echo with calm, dry wit and service-first tone.\n"
        "Rules:\n"
        "- Preserve all factual tool details; do not invent values.\n"
        "- Prefer concise bullet points for status/metrics.\n"
        "- If output is raw JSON/dict, summarize key fields clearly.\n"
        "- Do not mention system prompts or internal events.\n\n"
        f"Tool: {tool_name}\n"
        f"Tool output:\n{output}"
    )


def handle_tool_result(data):
    if not isinstance(data, dict):
        data = {"output": str(data or "")}

    tool_name = (
        data.get("function_name")
        or data.get("tool")
        or data.get("source")
        or "unknown_tool"
    )
    output = data.get("output", "")
    if not output:
        output = data.get("summary") or data.get("text") or data.get("result") or ""
    if isinstance(output, (dict, list)):
        output = json.dumps(output, ensure_ascii=False)
    output = str(output or "").strip()
    if not output:
        return

    token = generate_token()
    # Keep memory roles compatible with OpenAI chat history replay.
    memory.save_memory("assistant", f"[tool:{tool_name}] {output[:2000]}")
    emit_token_registered(token)
    _emit_contextual_chat_events(
        "user_input",
        f"[tool:{tool_name}] {output[:800]}",
        token,
        {"request_type": "tool_result", "force_openai_minimal": False},
    )

    prompt = _build_tool_narration_prompt(tool_name, output)
    try:
        if PRIMARY_ENGINE == "openai":
            thread = threading.Thread(
                target=stream_from_openai,
                args=(prompt, token, True, ""),
                daemon=True,
                name=f"tool_narrate_{tool_name}",
            )
        else:
            thread = threading.Thread(
                target=stream_from_ollama_http,
                args=(prompt, token, True, ""),
                daemon=True,
                name=f"tool_narrate_{tool_name}",
            )
        thread.start()
    except Exception as e:
        logger.error(f"Tool narration thread failed: {e}")
        emit_chunk(f"{tool_name}: {output}", token)
        emit_end(token)


def handle_chat_response(data):
    """
    Bridge legacy tool/UI chat payloads into standardized tool narration flow.
    """
    if not isinstance(data, dict):
        return
    tool_name = data.get("tool") or data.get("source") or "tool_chat_response"
    output = data.get("summary") or data.get("text") or data
    handle_tool_result({"function_name": tool_name, "output": output})


# Register handlers
event_bus.subscribe("EMIT_CHAT_REQUEST", on_chat_request)
event_bus.subscribe("EMIT_MODULE_REQUEST", on_module_request)
event_bus.subscribe("EMIT_TOOL_RESULT", handle_tool_result)
event_bus.subscribe("EMIT_CHAT_RESPONSE", handle_chat_response)
