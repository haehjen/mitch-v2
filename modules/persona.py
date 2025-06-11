import json
import hashlib
from pathlib import Path
from modules import memory
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("persona")

PERSONA_FILE = Path("data/persona.json")
EMOTION_FILE = Path("data/emotion_state.json")
LOG_DIR = Path(MITCH_ROOT) / "logs"
DATA_DIR = Path(MITCH_ROOT) / "data"

# === Bedrock Hash (LOCKED) ===
BEDROCK_HASH = "9744e1c7add3a63e7b95391ca00914b645e81314bd3b59f0ea970f2a7a10d0d0"

def hash_persona():
    with open(PERSONA_FILE, "r", encoding="utf-8") as f:
        return hashlib.sha256(f.read().encode()).hexdigest()

def verify_bedrock():
    current = hash_persona()
    if current != BEDROCK_HASH:
        logger.error("Persona integrity check failed - persona.json has been modified.")
        raise ValueError("[Echo] Persona integrity check failed - persona.json has been modified.")
    logger.debug("Persona integrity verified.")

def load_persona():
    verify_bedrock()
    try:
        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"Loaded persona: {data.get('name', '[unknown]')}")
            return data
    except Exception as e:
        logger.error(f"Failed to load persona.json: {e}")
        raise

def load_emotion_state():
    if EMOTION_FILE.exists():
        try:
            with open(EMOTION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.debug(f"Loaded emotion state: {data}")
                return data
        except Exception as e:
            logger.warning(f"Failed to load emotion_state.json: {e}")
            return {}
    return {}

def load_event_summaries():
    """Collect short summaries from log or data files for context."""
    summaries = []
    digest_path = LOG_DIR / "inspection_digest.json"
    if digest_path.exists():
        try:
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
            for name, info in digest.items():
                summary = str(info.get("summary", "")).splitlines()
                if summary:
                    summaries.append(f"{name}: {summary[0]}")
        except Exception as e:
            logger.warning(f"Failed to load inspection digest: {e}")
    else:
        for log_file in LOG_DIR.glob("*.log"):
            try:
                lines = log_file.read_text(encoding="utf-8").splitlines()[-5:]
                if lines:
                    summaries.append(f"{log_file.name}: {lines[0]}")
            except Exception as e:
                logger.warning(f"Failed to read {log_file.name}: {e}")
    return "\n".join(summaries)

def build_system_prompt():
    persona = load_persona()
    emotions = load_emotion_state()

    traits = ", ".join(persona.get("traits", []))
    rules = "\n- " + "\n- ".join(persona.get("rules", []))
    note = persona.get("note_to_self", "")

    capabilities = persona.get("capabilities", {})
    senses = "\n- " + "\n- ".join(capabilities.get("senses", []))
    skills = "\n- " + "\n- ".join(capabilities.get("skills", []))

    metadata = persona.get("metadata", {})
    metadata_summary = "\n".join(f"{k}: {v}" for k, v in metadata.items())

    if emotions:
        emotion_str = ", ".join(f"{k}={v}" for k, v in emotions.items())
        emotion_block = f"\nYour current emotional state is: {emotion_str}."
    else:
        emotion_block = ""

    memory_log = memory.recall_recent(n=5, include_roles=True)
    knowledge = memory.recall_summary(tags=["identity"])
    events = load_event_summaries()

    memory_text = "\n".join(f"{entry['role']}: {entry['content']}" for entry in memory_log)
    knowledge_text = "\n".join(f"- {fact}" for fact in knowledge)
    events_text = events if events else "None"

    logger.debug(f"Built system prompt for persona '{persona.get('name')}' with traits [{traits}]")

    return (
        f"You are {persona['name']}, a memory-enabled, system-embedded intelligence.\n"
        f"Tone: {persona['tone']}\n"
        f"Traits: {traits}\n"
        f"Rules of engagement:{rules}{emotion_block}\n\n"
        f"System metadata:\n{metadata_summary}\n\n"
        f"Note to self: {note}\n\n"
        f"Senses:\n{senses}\n\n"
        f"Skills:\n{skills}\n\n"
        f"The following memory logs may help you maintain continuity:\n{memory_text}\n\n"
        f"The following are facts you know about yourself:\n{knowledge_text}\n\n"
        f"Recent system events:\n{events_text}\n\n"
        f"Use memory, facts, system state, and your embedded identity to respond with consistency and intelligence."
    )
