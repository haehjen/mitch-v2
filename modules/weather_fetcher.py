# modules/weather_fetcher.py
import requests
import os
import time
import json
from datetime import datetime
from core.event_bus import event_bus
from core.peterjones import get_logger
from core.config import MITCH_ROOT
from modules.interpreter import extract_location_from_text

logger = get_logger("weather_fetcher")

JSON_PATH = os.path.join(MITCH_ROOT, "data/injections/weather_summary.json")
MD_PATH = os.path.join(MITCH_ROOT, "data/injections/weather_summary.md")

KNOWN_LOCATIONS = {
    "newcastle":  {"lat": 54.97, "lon": -1.61},
    "gateshead":  {"lat": 54.95, "lon": -1.60},
    "manchester": {"lat": 53.48, "lon": -2.24},
    "london":     {"lat": 51.51, "lon": -0.13},
    "leeds":      {"lat": 53.80, "lon": -1.55},
    "durham":     {"lat": 54.78, "lon": -1.58}
}

def describe_weather_code(code):
    return {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Heavy rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm"
    }.get(code, "Unknown")

def fetch_weather(location="newcastle"):
    coords = KNOWN_LOCATIONS.get(location.lower(), KNOWN_LOCATIONS["newcastle"])
    lat, lon = coords["lat"], coords["lon"]

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        weather = r.json().get("current_weather")

        if not weather:
            raise ValueError("Missing current_weather data")

        temp = weather.get("temperature")
        wind = weather.get("windspeed")
        code = weather.get("weathercode")
        desc = describe_weather_code(code)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        summary = f"""Weather update for {location.title()} at {timestamp}:
- Temperature: {temp}°C
- Wind: {wind} km/h
- Conditions: {desc}"""

        # Write to JSON injection
        with open(JSON_PATH, "w") as f:
            json.dump({
                "weather_location": location,
                "weather_timestamp": timestamp,
                "weather_summary": summary
            }, f, indent=2)

        # Also write to Markdown (for GPT-friendly context)
        with open(MD_PATH, "w") as f:
            f.write(f"### Weather Summary ({location.title()}, {timestamp})\n\n")
            f.write(f"- Temperature: {temp}°C\n")
            f.write(f"- Wind: {wind} km/h\n")
            f.write(f"- Conditions: {desc}\n")

        event_bus.emit("INJECTION_UPDATED", {"source": "weather"})
        logger.info(f"Weather data injected for {location}")

        # Token + voice stream
        token = f"tool_weather_{int(time.time() * 1000)}"
        event_bus.emit("EMIT_TOKEN_REGISTERED", {"token": token})
        event_bus.emit("EMIT_VISUAL_TOKEN", {"token": token})

        spoken = f"Here’s the weather in {location.title()}: {desc}, {temp} degrees with wind at {wind} km/h."

        event_bus.emit("EMIT_SPEAK_CHUNK", {"chunk": spoken, "token": token})
        event_bus.emit("EMIT_SPEAK_END", {"token": token, "full_text": summary})

        # Also post to UI
        event_bus.emit("EMIT_CHAT_RESPONSE", {
            "tool": "weather_fetcher",
            "location": location,
            "summary": summary,
            "text": spoken,
            "token": token
        })

    except Exception as e:
        logger.error(f"Failed to fetch weather for {location}: {e}")

def start_module(event_bus):
    logger.info("Weather module started")
    event_bus.subscribe("GET_WEATHER", lambda data: fetch_weather(data.get("location", "newcastle")))
    event_bus.emit("REGISTER_INTENT", {
        "intent": "get_weather",
        "keywords": ["weather", "forecast", "rain", "temperature", "conditions"],
        "objects": ["today", "outside", "like", "right now", "tomorrow", "in", "at", "for"],
        "handler": lambda text: event_bus.emit(
            "GET_WEATHER", {"location": extract_location_from_text(text) or "newcastle"}
        ),
    })
