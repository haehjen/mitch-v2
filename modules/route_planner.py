# modules/route_planner.py
import requests
from core.event_bus import event_bus
from core.peterjones import get_logger

logger = get_logger("route_planner")

ORS_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjBhYzEzYTA0ZmIwZDQyYWQ4OGY1YjViNzgxNmNjMjk4IiwiaCI6Im11cm11cjY0In0="

def plan_route(coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_KEY, "Content-Type": "application/json"}
    body = {
        "coordinates": coords  # e.g., [[lon1, lat1], [lon2, lat2], ...]
    }
    r = requests.post(url, json=body, headers=headers)
    if r.ok:
        data = r.json()
        # parse steps, distances, bearings, etc.
        # write to injection or emit UI data
    else:
        logger.error(f"Route planning failed: {r.status_code}")

def start_module(event_bus):
    event_bus.subscribe("PLAN_ROUTE", lambda data: plan_route(data["coords"]))
