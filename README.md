# MITCH v2

MITCH is a modular Python framework that coordinates several threads to create an "Echo" assistant. Modules handle speech input/output, memory, and other tasks while `main.py` wires them together using a simple event bus.
## Usage

1. **Set environment variables**
   - `OPENAI_API_KEY` – OpenAI API key used by the GPT components.
     If this variable isn't set, some modules will try to read the key from a
     file named `mitchskeys` in the project root (format: `OPENAI_API_KEY=...`).
   - `MITCH_DEBUG` *(optional)* – set to `true` for verbose logging.
   - `MITCH_SPEAKER_DEBUG` *(optional)* – enables additional speaker logs.
   - `PROXMOX_PASSWORD` *(optional)* – required when using the `proxmon` module.

2. **Run the entry point**
   ```bash
   python main.py
   ```
   The script starts the core modules and keeps running until interrupted.

## Installing dependencies

Install Python requirements (if a `requirements.txt` is present) with:

```bash
pip install -r requirements.txt
```

## Registering intents

Modules can contribute new phrases by emitting a `REGISTER_INTENT` event when they
start up. The event payload must include:

- `intent` – unique name for the intent.
- `keywords` – list of words used for matching.
- `objects` – optional secondary words.
- `handler` – callable invoked with the original text when the intent matches.

Example:

```python
event_bus.emit("REGISTER_INTENT", {
    "intent": "get_weather",
    "keywords": ["weather", "forecast"],
    "objects": ["in", "at", "for"],
    "handler": lambda text: event_bus.emit("GET_WEATHER", {"location": "newcastle"})
})
```

The interpreter stores the keywords and objects in
`data/injections/intents.json` so newly registered intents are immediately
available for matching.

