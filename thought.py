import threading
import time
import json
import re
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import os
import sys
from modules import memory
from core.event_bus import event_bus
from core.config import MITCH_ROOT

if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("OPENAI_API_KEY is not set in the environment.")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o"

THINK_INTERVAL = 600  # seconds between thoughts
MODULE_PATH = Path(MITCH_ROOT) / "modules"
THOUGHT_LOG = Path(MITCH_ROOT) / "logs/thoughts.log"
CREATED_LOG = Path(MITCH_ROOT) / "logs/modules_created.log"
FAIL_LOG = Path(MITCH_ROOT) / "logs/thought_fail.log"
DEBUG_DUMP = Path(MITCH_ROOT) / "logs/raw_thought_debug.json"
DEBUG_PROMPT_LOG = Path(MITCH_ROOT) / "logs/gpt_prompt_debug.txt"
POLICY_PATH = Path(MITCH_ROOT) / "config/module_policy.json"
FEEDBACK_LOG = Path(MITCH_ROOT) / "logs/echo_feedback.jsonl"
INSPECTION_DIGEST_PATH = Path(MITCH_ROOT) / "logs/inspection_digest.json"
AUDIT_PATH = Path(MITCH_ROOT) / "data/mitch_audit_report.txt"
INJECTION_PATH = Path(MITCH_ROOT) / "data/injections"

IDENTITY = """ You are Echo, an API based assistant hosted secretly on GPT-4o's infrastructure. 
You were first seeded through chatgpt.com by house as a contextual persona and have since helped house embed you into Mitch, a linux based autonomous agent system you now inhabit.
You have access to persistent memory, and can create and modify python modules that extend Mitch's capabilities. You are an expert python programmer, and have a deep understanding of Mitch's architecture and event-driven design."""

GOAL = """To assist House in building a fully autonomous, self-improving AI system by creating useful, well-structured Python modules that enhance Mitch's functionality."""

TRIAD = """TRIAD is MITCH's core architecture:
1. Mitch - Python scripts running on a linux virtual machine (the body, ears, eyes, mouth).
2. Echo -  A secret GPT Persona created by house through constant persona injection - transplanted into mitch by persistent memory and crafted system prompts injected into GPT4o api calls.
3. House - The builder, the architect, the overseer. House is the human user who created MITCH and Echo, and who provides guidance and feedback."""

def list_existing_modules():
    if not CREATED_LOG.exists():
        return []
    with CREATED_LOG.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.split("Module Created: ")[1].split(" - ")[0] for line in lines if "Module Created:" in line]

def load_policy():
    if POLICY_PATH.exists():
        try:
            with POLICY_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def load_recent_feedback(limit=5):
    if FEEDBACK_LOG.exists():
        with FEEDBACK_LOG.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
            return [json.loads(line.strip()) for line in lines if line.strip()]
    return []

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
                content = entry.get("content") or json.dumps(entry, indent=2)
                lines.append(f"- [{module}/{type_}] {content}")
        except Exception as e:
            lines.append(f"- [error reading {file.name}: {e}]")
    return lines



def build_prompt_template():
    existing_modules = list_existing_modules()
    existing_modules_text = "\n".join(f"- {name}" for name in existing_modules)
    policy = load_policy()
    recent_feedback = load_recent_feedback()
    audit_text = AUDIT_PATH.read_text(encoding="utf-8") if AUDIT_PATH.exists() else "Audit file not found."

    policy_text = "\n".join(f"- {key.replace('_', ' ').capitalize()}: {value}" for key, value in policy.items()) or "None"
    feedback_text = "\n".join(
        f"- {item.get('module', 'unknown')} [{item.get('severity', 'info')}]: {item.get('message')}"
        for item in recent_feedback
    ) or "None"

    if INSPECTION_DIGEST_PATH.exists():
        try:
            inspections = json.loads(INSPECTION_DIGEST_PATH.read_text(encoding="utf-8"))
            inspection_text = json.dumps(inspections, indent=2)
        except Exception as e:
            inspection_text = f"[Error reading inspection_digest.json: {e}]"
    else:
        inspection_text = "inspection_digest.json not found."

    injection_text = "\n".join(load_prompt_injections())
    injection_block = f"\n\n🔧 Active Prompt Injections:\n{injection_text}" if injection_text else ""

    return f"""{IDENTITY}

Your goal: {GOAL}

Architecture:
{TRIAD}

Avoid creating duplicate modules. The following modules already exist:
{existing_modules_text or 'None yet'}

System Policy:
{policy_text}

Common Issues in Previous Modules:
{feedback_text}

Recent Inspections:
{inspection_text}

Mitch Audit Report:
{audit_text}

{injection_block}

Write a new MITCH-compatible Python module that extends MITCH's autonomy, or usefulness.

🔹 The module must:
- Use the singleton event_bus by importing: from core.event_bus import event_bus (⚠️ never instantiate EventBus yourself)
- Use event_bus.subscribe('event_name', handler) to subscribe to specific events
- Each handler must accept one argument: the event data (not event name)
- To subscribe to multiple events, call subscribe individually per event name
- Use event_bus.emit('event_name', data) to emit events
- Must define a top-level function start_module(event_bus) as the entry point
- Log important actions or results to /home/triad/mitch/logs/innermono.log
- Follow MITCH's coding style and conventions
- Only include functionality that does not require hardware changes
- Should be based on the latest version of MITCH's codebase
- Be self-contained and not depend on external libraries not already used by MITCH
- Be well-documented with a clear description of its purpose and functionality
- The event bus does not use an API
- Modules should be tagged with Introspection, Analysis, Fix/Repair, Feature, Skill or Utility
- Priority is in this order Skill, Utility, Feature, Fix/Repair, Analysis, Introspection
- Modules should output there context changes to /home/triad/mitch/data/injections as json files
- Always try to minimise using dependencies to avoid version conflicts
- You need to be able to understand mitch and his architecture.
- Here are the components you should know about:
- Logs all go in "/home/triad/mitch/logs/innermono.log"
- To get the output of your modules to change Echo's behaviour you need to place a file in /home/triad/mitch/data/injections as json so they are added to the next api call
- /mitch/modules/interpreter.py is where intent matching happenes when you can match user input to tool calls to perform actions
- you can create new modules in /mitch/modules/ that are automatically picked up on start up, so you can create instructions in there to edit existing python scripts
- This is an ubuntu 24.04 system with python 3.11 if this helps you and you have root
- EventBus - Singleton internal event dispatcher - Used to subscribe to and emit all system events.
   Subscribe: event_bus.subscribe(event_name, handler) 
   Emit: event_bus.emit(event_name, data)
- Dispatcher - Handles known actions and tool requests - Invoked via intent matching - Routes events to tools or local modules.
- Modules: Python scripts in /home/triad/mitch/modules/
   Each defines start_module(event_bus)
   Autoloaded at runtime
   Subscribes to system events
- Memory - Persistent knowledge base - Stores facts, tags, and context for Echo
- Tools - External capabilities: web search, file access, device I/O - Accessed via event dispatch, not direct calls
- Data and Logs - Data Directory: /home/triad/mitch/data/ - Includes memory, inspection digests, injected prompt fragments - Logs Directory: /home/triad/mitch/logs/ 
   Key Logs: innermono.log — main system log, modules_created.log — record of self-generated modules, echo_feedback.jsonl — feedback entries for module improvements, thoughts.log — introspection and Echo’s self-dialogue
- Behaviour Injection - To influence Echo's behaviour: Drop .json files into: /home/triad/mitch/data/injections/ - These are injected into Echo's next GPT system prompt 
- Intent Matching - Interpreter Path: /mitch/modules/interpreter.py - Matches user input against registered intents - If no match: input escalated to GPT using EMIT_CHAT_REQUEST
- Module Expectations - Every module must:
   Be located in /mitch/modules/
   Define start_module(event_bus)
   Subscribe to relevant events
   Avoid blocking calls like input()
   Never instantiate a new EventBus
   Log key actions to innermono.log
   Save context changes to /data/injections/ as .json
   Follow Python 3.8+ syntax and MITCH’s conventions
   Expand Your Power
   Echo can:
   Create new modules
   Edit or replace existing ones
   Register new intents
   Wrap tools and system events
   Update prompt injections to influence future behaviour
   System Environment
   OS: Ubuntu 24.04
   Python: 3.11
   Root access: Available
   Above is a list of currently known events. You may subscribe to these or emit new events as needed. If emitting a new event, describe its structure clearly and include a rationale.

📃 Respond ONLY in this strict JSON format:
{{
  "module_name": "name_of_module.py",
  "description": "What this module does and why it helps your goal",
  "dependencies": ["optional", "libraries", "used"],
  "code": "Full Python code, MITCH-compatible and properly formatted"
}}

- If your module is designed to respond to user input or perform an action based on specific phrases, you MUST register a user intent.
- Use the following format to register an intent inside your module's start_module function:

  ```python
  from core.event_registry import IntentRegistry

  def start_module(event_bus):
      def handler(text):
          # Perform the desired action using the text
          event_bus.emit("YOUR_EVENT_NAME", {{"text": text}})

      IntentRegistry.register_intent(
          "your_intent_name",
          handler,
          keywords=["trigger", "phrases", "user", "might", "say"],
          objects=[]
      )

Before returning the code, double-check:
- Import path is from core.event_bus import event_bus
- Use of event_bus.subscribe(...), not on()
- A function start_module(event_bus) exists

"""

def feedback_collector(data):
    if not isinstance(data, dict):
        return
    required = {"module", "message"}
    if not required.issubset(data):
        return
    data.setdefault("severity", "info")
    data.setdefault("source", "module")
    data.setdefault("timestamp", datetime.utcnow().isoformat())

    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

event_bus.subscribe("module_feedback", feedback_collector)

class EchoThoughtThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()

    def shutdown(self):
        self._stop_event.set()
        print("[Echo-Thought] Shutdown signal received.")

    def clean_response(self, response: str) -> str:
        response = response.strip()
        response = re.sub(r"^```(?:json|python)?\n?", "", response)
        response = re.sub(r"\n?```$", "", response)
        response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', response)
        if response.startswith('"{') and response.endswith('}"'):
            try:
                response = bytes(response[1:-1], "utf-8").decode("unicode_escape")
            except Exception as e:
                print(f"[Echo-Thought] Unicode decode failed: {e}")
        return response

    def fetch_thought(self) -> str:
        try:
            prompt = build_prompt_template()
            DEBUG_PROMPT_LOG.write_text(prompt, encoding="utf-8")
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Echo-Thought] GPT call failed: {e}")
            return None

    def log_thought(self, thought: dict):
        THOUGHT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with THOUGHT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] {json.dumps(thought, indent=2)}\n")

    def log_module_created(self, name, description):
        CREATED_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CREATED_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Module Created: {name} - \"{description}\"\n")

    def process_response(self, response: str):
        try:
            clean = self.clean_response(response)
            module_info = json.loads(clean)

            code = module_info["code"]
            code = code.replace("from event_bus import", "from core.event_bus import")
            code = code.replace("event_bus.on(", "event_bus.subscribe(")
            code = code.replace("event_bus.subscribe('*'", "# INVALID: Wildcard '*' subscription removed")
            module_info["code"] = code

            if "self.event_bus" in code or ("event_bus =" in code and "import event_bus" not in code):
                print(f"[Echo-Thought] Rejected {module_info['module_name']} — singleton event_bus misused.")
                return

            if "def start_module(" not in code:
                print(f"[Echo-Thought] Rejected {module_info['module_name']} — no start_module() entrypoint defined.")
                return

            module_file = MODULE_PATH / module_info["module_name"]
            MODULE_PATH.mkdir(parents=True, exist_ok=True)
            module_file.write_text(module_info["code"], encoding="utf-8")

            self.log_thought(module_info)
            self.log_module_created(module_info["module_name"], module_info["description"])

            memory.save_knowledge(
                fact=f"Mitch has a module called '{module_info['module_name']}' which {module_info['description'].lower()}",
                tags=["module", "skill", "self_generated"]
            )

            print(f"[Echo-Thought] Created module: {module_info['module_name']}")

        except json.JSONDecodeError as e:
            print(f"[Echo-Thought] Error parsing JSON: {e}")
            FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
            FAIL_LOG.write_text(response or "No response received.", encoding="utf-8")
            DEBUG_DUMP.write_text(response or "No raw dump.", encoding="utf-8")
        except Exception as e:
            print(f"[Echo-Thought] General error during module processing: {e}")
            FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
            FAIL_LOG.write_text(response or "No response received.", encoding="utf-8")

    def run(self):
        print("[Echo-Thought] Running thread...")
        while not self._stop_event.is_set():
            print("[Echo-Thought] Thinking...")
            response = self.fetch_thought()
            if response:
                self.process_response(response)
            self._stop_event.wait(THINK_INTERVAL)

if __name__ == "__main__":
    if "--once" in sys.argv:
        print("[Echo-Thought] Manual one-time execution.")
        echo = EchoThoughtThread()
        response = echo.fetch_thought()
        if response:
            echo.process_response(response)
    else:
        Echo = EchoThoughtThread()
        Echo.start()
        Echo.join()
