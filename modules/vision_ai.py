# modules/vision_ai.py

import openai
import os
from dotenv import load_dotenv
from modules.vision import VisionModule

# Load secrets
load_dotenv(dotenv_path="mitchskeys")

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Public image URL served by Flask + NGINX
CAMERA_URL = "https://mitch.andymitchell.online/latest.jpg"

class VisionAI:
    def __init__(self):
        self.vision_module = VisionModule()

    async def capture_and_describe(self):
        try:
            self.vision_module.capture_image()
        except Exception as e:
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
