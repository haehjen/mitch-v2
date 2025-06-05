# MITCH v2

MITCH is a modular Python framework that coordinates several threads to create an "Echo" assistant. Modules handle speech input/output, memory, and other tasks while `main.py` wires them together using a simple event bus.
## Usage

1. **Set environment variables**
   - `OPENAI_API_KEY` – OpenAI API key used by the GPT components.
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

