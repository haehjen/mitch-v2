import os
from openai import OpenAI
from modules.vision import VisionModule
from core.peterjones import get_logger

logger = get_logger("vision_ai")

# Public image URL served by Flask + NGINX
CAMERA_URL = "https://mitch.andymitchell.online/latest.jpg"

class VisionAI:
    def __init__(self):
        self.vision_module = VisionModule()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("[VisionAI] OPENAI_API_KEY not set; vision features may fail.")
        self.client = OpenAI(api_key=api_key)

    async def capture_and_describe(self):
        try:
            self.vision_module.capture_image()
        except Exception as e:
            logger.error(f"Failed to capture image: {e}")
            return f"[VisionAI] Failed to capture image: {e}"

        response = self.client.chat.completions.create(
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

        response = self.client.chat.completions.create(
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
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "[VisionAI] Error: OPENAI_API_KEY not set."
        client = OpenAI(api_key=api_key)
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
