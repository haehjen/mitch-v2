import json
from datetime import datetime
from pathlib import Path

MEMORY_LOG = Path("data/memory.jsonl")
KNOWLEDGE_BASE = Path("data/knowledge.json")
MEMORY_LOG.parent.mkdir(parents=True, exist_ok=True)

# === Memory ===

def save_memory(role, content):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "role": role,
        "content": content
    }
    with open(MEMORY_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

def recall_recent(n=5, include_roles=False):
    if not MEMORY_LOG.exists():
        return []
    with open(MEMORY_LOG, "r") as f:
        lines = f.readlines()[-n:]
        if include_roles:
            return [json.loads(line) for line in lines]
        else:
            return [json.loads(line)["content"] for line in lines]

def clear_memory():
    if MEMORY_LOG.exists():
        MEMORY_LOG.unlink()

# === Knowledge ===

def load_knowledge():
    if KNOWLEDGE_BASE.exists():
        with open(KNOWLEDGE_BASE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict) and "facts" in data:
                return data["facts"]
            return data  # fallback for legacy format
    return []

def save_knowledge(fact, tags=None):
    if tags is None:
        tags = []
    current_data = {}
    if KNOWLEDGE_BASE.exists():
        with open(KNOWLEDGE_BASE, "r") as f:
            try:
                current_data = json.load(f)
            except json.JSONDecodeError:
                current_data = {}

    facts = current_data.get("facts", []) if isinstance(current_data, dict) else current_data
    facts.append({
        "fact": fact,
        "tags": tags,
        "timestamp": datetime.utcnow().isoformat()
    })

    new_data = {"facts": facts}
    with open(KNOWLEDGE_BASE, "w") as f:
        json.dump(new_data, f, indent=2)

def recall_summary(tags=None):
    knowledge = load_knowledge()
    if not isinstance(knowledge, list):
        return []

    if tags:
        return [
            entry["fact"]
            for entry in knowledge
            if isinstance(entry, dict) and "tags" in entry and any(tag in entry["tags"] for tag in tags)
        ]
    else:
        return [
            entry["fact"]
            for entry in knowledge
            if isinstance(entry, dict) and "fact" in entry
        ]

# === Context Management ===

def truncate_tail():
    if not MEMORY_LOG.exists():
        return
    lines = MEMORY_LOG.read_text().splitlines()
    if not lines:
        return
    last = json.loads(lines[-1])
    if last["role"] == "user":
        print("[Memory] Removing unpaired user prompt from memory.jsonl")
        lines.pop()
        MEMORY_LOG.write_text("\n".join(lines) + "\n")

def clear_temp_context():
    truncate_tail()
