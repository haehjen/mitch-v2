import json
import os
import re
import time

from core.event_bus import event_bus
from core.peterjones import get_logger
from core.config import MITCH_ROOT
from modules.web_search import ddgs_news_search
from modules.geocode import geocode_location

class ProtestTracker:
    def __init__(self):
        self.logger = get_logger("protest_tracker")
        self.protests_log = []
        self.last_run = 0
        self.min_interval = 300  # seconds (5 minutes)
        self.seen_ids = set()    # de-dupe across runs

        # Local+national sources to poll (DuckDuckGo News)
        self.sources = [
            # National baseline
            "site:bbc.co.uk",
            # North East + Teesside local press
            "site:chroniclelive.co.uk",     # Newcastle, Sunderland, Tyneside, Wearside
            "site:gazettelive.co.uk",       # Teesside Live (Middlesbrough)
            "site:sunderlandecho.com",      # Sunderland Echo
            "site:shieldsgazette.com",      # South Shields / Tyneside
            "site:thenorthernecho.co.uk",   # The Northern Echo
            "site:hartlepoolmail.co.uk",    # Hartlepool / Peterlee area
            "site:durhamadvertiser.co.uk",  # Durham / County Durham
        ]

        # Query terms to match likely reports
        self.terms = [
            "protest", "demonstration", "march", "rally", "vigil"
        ]

    def check_for_protests(self, event_data):
        now = time.time()
        if now - self.last_run < self.min_interval:
            return
        self.last_run = now

        try:
            all_results = []
            # Build focused queries per source; bias to your local towns
            loc_hint = "(Sunderland OR Newcastle OR Peterlee OR Teesside OR Middlesbrough OR Durham OR Hartlepool OR Gateshead)"
            joined_terms = " OR ".join(self.terms)
            for src in self.sources:
                q = f"{joined_terms} {loc_hint} {src}"
                results = ddgs_news_search(q, max_results=15) or []
                all_results.extend(results)

            protests = self.parse_results(all_results)
            if protests:
                self.protests_log.extend(protests)
                self._log_to_file(protests)
                self.emit_protest_updates(protests)
                self.save_protest_data(protests)
        except Exception as e:
            self.logger.error(f"Error fetching protest data: {e}")

    def parse_results(self, results):
        protests = []
        for r in results:
            title = r.get("title", "")
            snippet = r.get("body", "")
            url = r.get("url", "")
            # Basic de-dupe id
            rid = (title or url).strip().lower()
            if not rid or rid in self.seen_ids:
                continue
            location = self.extract_location(title + " " + snippet)
            if location:
                item = {
                    "location": location,
                    "description": title,
                    "timestamp": time.time(),
                    "url": url,
                    "source": r.get("source", "")
                }
                protests.append(item)
                self.seen_ids.add(rid)
        return protests

    def extract_location(self, text):
        """Pick out a city/place with emphasis on North East/Teesside.

        Uses simple word-boundary matching with a few aliases folded to a
        canonical label that geocoder understands well.
        """
        city_map = {
            # NE & Teesside focus
            "Newcastle": ["newcastle", "newcastle upon tyne"],
            "Sunderland": ["sunderland"],
            "Peterlee": ["peterlee", "east durham"],
            "Teesside": ["teesside", "teeside", "tees-side"],
            "Middlesbrough": ["middlesbrough"],
            "Hartlepool": ["hartlepool"],
            "Stockton-on-Tees": ["stockton", "stockton-on-tees"],
            "Redcar": ["redcar"],
            "Gateshead": ["gateshead"],
            "South Shields": ["south shields"],
            "Durham": ["durham", "county durham"],
            "Darlington": ["darlington"],
            # Wider UK
            "Glasgow": ["glasgow"],
            "Leeds": ["leeds"],
            "Sheffield": ["sheffield"],
            "Birmingham": ["birmingham"],
            "Manchester": ["manchester"],
            "Liverpool": ["liverpool"],
            "Bristol": ["bristol"],
            "Cardiff": ["cardiff"],
            "London": ["london"],
        }

        tl = text.lower()
        for canon, aliases in city_map.items():
            for a in aliases:
                if re.search(rf"\b{re.escape(a)}\b", tl, re.IGNORECASE):
                    # Prefer Teesside to Middlesbrough if headline says Teesside
                    return canon
        return None

    def _log_to_file(self, protests):
        for protest in protests:
            self.logger.info(
                f"Protest logged: {protest['description']} at {protest['location']}"
            )

    def emit_protest_updates(self, protests):
        event_bus.emit("EMIT_CHECK_PROTESTS", protests)
        for protest in protests:
            coords = geocode_location(protest["location"])
            if coords:
                lat, lon = coords
                event_bus.emit("EMIT_MAP_PIN", {
                    "label": "Protest",
                    "location": protest["location"],
                    "description": protest["description"],
                    "lat": lat,
                    "lon": lon
                })
            else:
                self.logger.warning(f"Could not geocode: {protest['location']}")

    def save_protest_data(self, protests):
        data = {
            "protests": protests,
            "timestamp": time.time(),
        }
        path = os.path.join(MITCH_ROOT, "data", "injections", "protest_data.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

protest_tracker = ProtestTracker()

def handle_heartbeat(event_data):
    protest_tracker.check_for_protests(event_data)

def start_module(event_bus):
    event_bus.subscribe("ECHO_HEARTBEAT", handle_heartbeat)
    get_logger("protest_tracker").info("Protest Tracker module started.")
