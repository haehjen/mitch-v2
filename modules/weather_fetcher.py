# modules/weather_fetcher.py
import requests
import os
import json
from datetime import datetime
from threading import Thread
from core.event_bus import event_bus
from core.peterjones import get_logger
from core.config import MITCH_ROOT

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
    logger.info(f"[weather_fetcher] Fetching weather for: {location}")
    coords = KNOWN_LOCATIONS.get(location.lower(), KNOWN_LOCATIONS["newcastle"])
    lat, lon = coords["lat"], coords["lon"]

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        logger.info(f"[weather_fetcher] Requesting URL: {url}")
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

        with open(JSON_PATH, "w") as f:
            json.dump({
                "weather_location": location,
                "weather_timestamp": timestamp,
                "weather_summary": summary
            }, f, indent=2)

        with open(MD_PATH, "w") as f:
            f.write(f"### Weather Summary ({location.title()}, {timestamp})\n\n")
            f.write(f"- Temperature: {temp}°C\n")
            f.write(f"- Wind: {wind} km/h\n")
            f.write(f"- Conditions: {desc}\n")

        event_bus.emit("INJECTION_UPDATED", {"source": "weather"})
        logger.info(f"Weather data injected for {location}")

        event_bus.emit(
            "EMIT_TOOL_RESULT",
            {
                "function_name": "weather_fetcher",
                "output": {
                    "location": location,
                    "temperature_c": temp,
                    "wind_kmh": wind,
                    "conditions": desc,
                    "timestamp": timestamp,
                },
                "summary": summary,
            },
        )

    except Exception as e:
        logger.error(f"[weather_fetcher] Failed to fetch weather for {location}: {e}")

def start_module(event_bus):
    logger.info("Weather module started")
    def _start_weather_job(data):
        t = Thread(
            target=fetch_weather,
            args=((data or {}).get("location", "newcastle"),),
            daemon=True,
            name="weather_fetcher_job",
        )
        t.start()

    event_bus.subscribe("GET_WEATHER", _start_weather_job)

    from core.event_registry import IntentRegistry

    def weather_handler(text):
        location = "newcastle"
        for loc in KNOWN_LOCATIONS:
            if loc in text.lower():
                location = loc
                break
        event_bus.emit("GET_WEATHER", {"location": location})

    IntentRegistry.register_intent(
        name="get_weather",
        handler=weather_handler,
        keywords=["weather", "forecast", "temperature", "wind", "conditions"],
        objects=list(KNOWN_LOCATIONS.keys())
    )
