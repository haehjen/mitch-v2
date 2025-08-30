import threading
import json
import re
from openai import OpenAI
from pathlib import Path
import os
from core.event_bus import event_bus
from core.peterjones import get_logger
from modules import memory, persona
from core.config import MITCH_ROOT

try:
    import ollama  # type: ignore
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

logger = get_logger("gptv2")

if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY not found; GPT features will fail unless set.")

client = OpenAI()

OPENAI_MODEL = "gpt-4o"
OLLAMA_MODEL = "mistral"
MEMORY_WINDOW = 8
INJECTION_PATH = Path(MITCH_ROOT) / "data" / "injections"

active_token = None


def load_prompt_injections():
    if not INJECTION_PATH.exists():
        return []
    lines = []
    for file in sorted(INJECTION_PATH.glob("*.json")):
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
            items = raw if isinstance(raw, list) else [raw]
            for entry in items:
                module = file.stem
                type_ = entry.get("type", "misc")
                content = entry.get("content", json.dumps(entry))
                if content:
                    safe_content = content.encode("utf-8", errors="replace").decode("utf-8")
                    lines.append(f"- [{module}/{type_}] {safe_content}")
        except Exception as e:
            lines.append(f"- [error reading {file.name}: {e}]")
    return lines


def build_system_prompt():
    base = persona.build_system_prompt()
    injections = load_prompt_injections()
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


def emit_end(token):
    event_bus.emit("EMIT_SPEAK_END", {"token": token})


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
    prompt = data.get("prompt", "")
    token = generate_token()
    active_token = token
    emit_token_registered(token)
    logger.info(f"New chat request: {prompt} (token: {token})")

    try:
        thread = threading.Thread(target=stream_from_openai, args=(prompt, token))
        thread.start()
    except Exception as e:
        logger.error(f"OpenAI thread start failed: {e}")
        fallback_or_fail(prompt, token)


def stream_from_openai(prompt, token):
    try:
        system_prompt = build_system_prompt()

        # Recall recent turns WITHOUT the current prompt (since we haven't saved it yet)
        recent = memory.recall_recent(n=MEMORY_WINDOW, include_roles=True)

        # Summarized facts / long-term memory
        facts = memory.recall_summary()
        fact_string = "\n".join(f"- {fact}" for fact in facts[:5])
        knowledge_context = f"The following facts are known and persistent:\n{fact_string}"

        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n{knowledge_context}"},
            *[{"role": entry["role"], "content": entry["content"]} for entry in recent],
            {"role": "user", "content": prompt},
        ]

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            stream=True,
        )

        response_buffer = ""
        for chunk in response:
            part = chunk.choices[0].delta.content
            if part:
                response_buffer += part
                emit_chunk(part, token)

        emit_end(token)

        # Persist AFTER completion to avoid duplicate user message in recall()
        memory.save_memory("user", prompt)
        memory.save_memory("assistant", response_buffer)

        maybe_emit_module_create(response_buffer)

    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        fallback_or_fail(prompt, token)


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
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            stream=False,
        )

        if not response.choices:
            raise ValueError("Empty choices in GPT response")

        full_response = response.choices[0].message.content
        memory.save_memory("assistant", full_response)
        maybe_emit_module_create(full_response)
        emit_chunk(full_response, token)
        emit_end(token)

    except Exception as e:
        logger.error(f"Module generation failed: {e}")
        fallback_or_fail(prompt, token)


def fallback_or_fail(prompt, token):
    if HAS_OLLAMA:
        fallback_to_ollama(prompt, token)
    else:
        logger.warning("Fallback not available. Emitting error message.")
        emit_chunk("Something went wrong.", token)
        emit_end(token)


def fallback_to_ollama(prompt, token):
    logger.info(f"Falling back to Ollama: {OLLAMA_MODEL}")
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        for part in response["message"]["content"].split():
            emit_chunk(part + " ", token)
        emit_end(token)

        # Keep memory order consistent with main path
        memory.save_memory("user", prompt)
        memory.save_memory("assistant", response["message"]["content"])
    except Exception as e:
        logger.error(f"Ollama failed: {e}")
        emit_chunk("Fallback failed too. Sorry.", token)
        emit_end(token)


def on_chat_request(data):
    handle_chat_request(data)


def on_module_request(data):
    handle_module_request(data)


def handle_tool_result(data):
    tool_name = data.get("function_name", "unknown")
    output = data.get("output", "")
    token = generate_token()
    memory.save_memory("tool", f"{tool_name} result: {output}")
    emit_token_registered(token)

    emit_chunk(f"Tool '{tool_name}' returned: {output}", token)
    emit_end(token)


# Register handlers
event_bus.subscribe("EMIT_CHAT_REQUEST", on_chat_request)
event_bus.subscribe("EMIT_MODULE_REQUEST", on_module_request)
event_bus.subscribe("EMIT_TOOL_RESULT", handle_tool_result)