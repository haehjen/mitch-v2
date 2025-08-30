from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

_geolocator = Nominatim(user_agent="mitch_protest_tracker", timeout=10)

_cache = {}

def geocode_location(location: str) -> tuple[float, float] | None:
    """Convert a location name into (lat, lon) using OpenStreetMap."""
    if location in _cache:
        return _cache[location]

    try:
        geo = _geolocator.geocode(location + ", UK")
        if geo:
            coords = (geo.latitude, geo.longitude)
            _cache[location] = coords
            return coords
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None
