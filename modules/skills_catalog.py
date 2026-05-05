import time

from core.event_registry import IntentRegistry
from core.peterjones import get_logger

logger = get_logger("skills_catalog")

_bus = None


def _new_token() -> str:
    return f"skills_{int(time.time() * 1_000_000)}"


def _emit(text: str):
    if not _bus:
        return
    token = _new_token()
    _bus.emit("EMIT_TOKEN_REGISTERED", {"token": token})
    _bus.emit("EMIT_VISUAL_TOKEN", {"token": token})
    _bus.emit(
        "EMIT_SPEAK",
        {
            "text": text,
            "token": token,
            "source": "skills_catalog",
        },
    )


def _collect_intents():
    out = []
    for intent in IntentRegistry.intents:
        if not intent:
            continue
        source = getattr(getattr(intent, "handler", None), "__module__", "unknown")
        name = str(getattr(intent, "name", "") or "").strip()
        kws = [str(k).strip() for k in (getattr(intent, "keywords", []) or []) if str(k).strip()]
        if not name:
            continue
        out.append({"name": name, "source": source, "keywords": kws})
    return out


def _is_user_facing(entry: dict) -> bool:
    source = str(entry.get("source", ""))
    name = str(entry.get("name", ""))
    if source.startswith("modules.contextual_"):
        return False
    if source in {"modules.system_interaction_enhancer"}:
        return False
    if name.startswith("manual_"):
        return False
    return True


def _render_summary(intents: list[dict]) -> str:
    # Keep this short for speech.
    names = sorted({x["name"].replace("_", " ") for x in intents if _is_user_facing(x)})
    top = names[:14]
    if not top:
        return "I don't have a skills snapshot available yet."
    return (
        "Current skills snapshot: "
        + "; ".join(top)
        + ". Say skills all for the full list."
    )


def _render_full(intents: list[dict]) -> str:
    user_intents = [x for x in intents if _is_user_facing(x)]
    user_intents.sort(key=lambda x: x["name"])
    if not user_intents:
        return "No user-facing skills are registered right now."

    lines = ["Full skill list:"]
    for item in user_intents[:48]:
        name = item["name"].replace("_", " ")
        kws = item.get("keywords", [])
        if kws:
            lines.append(f"- {name} (trigger: {', '.join(kws[:4])})")
        else:
            lines.append(f"- {name}")
    return " ".join(lines)


def _handle_skills(text: str):
    msg = str(text or "").lower()
    intents = _collect_intents()
    if "all" in msg or "full" in msg or "everything" in msg:
        _emit(_render_full(intents))
        return
    _emit(_render_summary(intents))


def start_module(event_bus):
    global _bus
    _bus = event_bus

    IntentRegistry.register_intent(
        "skills_catalog",
        _handle_skills,
        keywords=["skills", "capabilities", "what can you do"],
        objects=[],
        priority=95,
    )
    logger.info("skills_catalog started (trigger: skills)")

