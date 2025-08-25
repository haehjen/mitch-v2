# modules/vision_ai.py

import openai
import os
from pathlib import Path
from dotenv import load_dotenv
from modules.vision import VisionModule
from core.peterjones import get_logger

# Load secrets
load_dotenv(dotenv_path="mitchskeys")

if not os.getenv("OPENAI_API_KEY"):
    key_path = Path(__file__).resolve().parent.parent / "mitchskeys"
    if key_path.exists():
        for line in key_path.read_text(encoding="utf-8").splitlines():
            if "OPENAI_API_KEY=" in line:
                os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not os.getenv("OPENAI_API_KEY"):
    print("[VisionAI] Warning: OPENAI_API_KEY not set; vision features may fail.")

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = get_logger("vision_ai")

# Public image URL served by Flask + NGINX
CAMERA_URL = "https://mitch.andymitchell.online/latest.jpg"

class VisionAI:
    def __init__(self):
        self.vision_module = VisionModule()

    async def capture_and_describe(self):
        try:
            self.vision_module.capture_image()
        except Exception as e:
            logger.error(f"Failed to capture image: {e}")
            return f"[VisionAI] Failed to capture image: {e}"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please describe this image."},
                        {"type": "image_url", "image_url": {"url": CAMERA_URL}}
                    ]
                }
            ],
            max_tokens=800,
            temperature=0.7
        )

        return response.choices[0].message.content

    async def detect_objects(self):
        try:
            self.vision_module.capture_image()
        except Exception as e:
            logger.error(f"Failed to capture image: {e}")
            return f"[VisionAI] Failed to capture image: {e}"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "List all objects you can identify in this image."},
                        {"type": "image_url", "image_url": {"url": CAMERA_URL}}
                    ]
                }
            ],
            max_tokens=800,
            temperature=0.7
        )

        return response.choices[0].message.content

def describe_image_from_url(image_url: str) -> str:
    """
    Uses GPT-4o vision to describe an image at a given public URL.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please describe this image clearly and concisely."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[VisionAI] Failed to describe image: {e}")
        return f"[VisionAI] Error: {e}"
