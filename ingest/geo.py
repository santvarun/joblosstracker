"""Geography helpers: resolve a city/state into coordinates and a region."""

from __future__ import annotations

from .config import CITY_INFO, STATE_TO_REGION

# Common aliases the news uses -> our canonical city name.
_CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "madras": "Chennai",
    "chennai": "Chennai",
    "trivandrum": "Thiruvananthapuram",
    "cochin": "Kochi",
    "kochi": "Kochi",
    "mysore": "Mysuru",
    "mangalore": "Mangaluru",
    "vizag": "Visakhapatnam",
    "new delhi": "New Delhi",
    "delhi": "Delhi",
    "ncr": "Delhi",
}


def canonical_city(city: str | None) -> str | None:
    """Map a free-text city name to one of our known cities, if possible."""
    if not city:
        return None
    key = city.strip().lower()
    if key in _CITY_ALIASES:
        return _CITY_ALIASES[key]
    # Exact (case-insensitive) match against known cities.
    for known in CITY_INFO:
        if known.lower() == key:
            return known
    return None


def resolve(city: str | None, state: str | None, region: str | None) -> dict:
    """Return a dict with normalized city, state, region, lat, lng.

    Region precedence: an explicit valid region from the extractor wins; else we
    derive it from the state; else from the city's state; else "Unknown".
    """
    c = canonical_city(city)
    st = state.strip() if state else None
    lat = lng = None

    if c and c in CITY_INFO:
        c_state, lat, lng = CITY_INFO[c]
        st = st or c_state

    derived_region = None
    if st and st in STATE_TO_REGION:
        derived_region = STATE_TO_REGION[st]

    final_region = region if region in STATE_TO_REGION.values() or region in (
        "Pan-India",
        "Unknown",
    ) else None
    final_region = final_region or derived_region or "Unknown"

    return {
        "city": c or (city.strip() if city else None),
        "state": st,
        "region": final_region,
        "lat": lat,
        "lng": lng,
    }
