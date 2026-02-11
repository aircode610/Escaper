"""
Google Maps API client for the enricher.

Uses:
- Geocoding API: address -> (lat, lng)
- Distance Matrix API: walking times/distances (1 origin, N destinations)
- Directions API: transit directions (one route per call; used for transit when Routes API unavailable)
- Routes API: transit route matrix (1 origin, N destinations, one request)
- Places API (New): nearby search (POST places:searchNearby)

Requires GOOGLE_MAPS_API_KEY in .env. Enable the APIs above in Google Cloud Console.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from typing import Any

# Default destinations for Bremen listings
DEFAULT_UNIVERSITY = "Constructor University, Campus Ring 1, 28759 Bremen, Germany"
DEFAULT_HBF = "Bremen Hauptbahnhof, Germany"

# ~15 min walk ≈ 1.2 km
NEARBY_RADIUS_M = 1200


def _get_api_key() -> str | None:
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    import config
    return config.get_google_maps_api_key()


def _request_get(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _request_post(url: str, body: dict, headers: dict) -> Any:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        # Routes API may return newline-delimited JSON stream; Places returns single JSON object
        lines = [ln.strip() for ln in raw.strip().split("\n") if ln.strip()]
        if len(lines) == 1:
            return json.loads(lines[0])
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
        if out:
            return out
        # Pretty-printed or single object with newlines: parse whole response
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


# ---------- Geocoding API ----------


def geocode(address: str, api_key: str | None = None) -> tuple[float, float] | None:
    """Return (lat, lng) for the given address. Uses Geocoding API."""
    key = api_key or _get_api_key()
    if not key or not (address or "").strip():
        return None
    q = urllib.parse.quote_plus(address.strip())
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={q}&key={key}"
    try:
        data = _request_get(url)
        if data.get("status") != "OK" or not data.get("results"):
            return None
        loc = data["results"][0]["geometry"]["location"]
        return (float(loc["lat"]), float(loc["lng"]))
    except Exception:
        return None


# ---------- Distance Matrix API (walking only) ----------


def distance_matrix(
    origin: str,
    destinations: list[str],
    mode: str = "walking",
    departure_time_unix: int | None = None,
    api_key: str | None = None,
) -> list[tuple[float, float] | None]:
    """
    Get travel duration (minutes) and distance (km) from origin to each destination.
    Uses Distance Matrix API. Use mode="walking" only (for transit use routes_transit_matrix or directions_transit).
    """
    key = api_key or _get_api_key()
    if not key or not origin or not destinations:
        return [None] * len(destinations)
    if mode != "walking":
        return [None] * len(destinations)
    orig_enc = urllib.parse.quote_plus(origin.strip())
    dest_enc = urllib.parse.quote_plus("|".join(d.strip() for d in destinations))
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={orig_enc}&destinations={dest_enc}&mode=walking&key={key}"
    try:
        data = _request_get(url)
        if data.get("status") != "OK":
            return [None] * len(destinations)
        rows = data.get("rows") or []
        if not rows:
            return [None] * len(destinations)
        elements = rows[0].get("elements") or []
        out = []
        for el in elements:
            if el.get("status") != "OK":
                out.append(None)
                continue
            dur = el.get("duration") or {}
            dist = el.get("distance") or {}
            mins = dur.get("value", 0) / 60.0
            km = dist.get("value", 0) / 1000.0
            out.append((mins, km))
        return out
    except Exception:
        return [None] * len(destinations)


# ---------- Directions API (transit, one route per call) ----------


def directions_transit(
    origin: str,
    destination: str,
    departure_time_unix: int,
    api_key: str | None = None,
) -> tuple[float, float] | None:
    """
    Get transit duration (minutes) and distance (km) from origin to destination.
    Uses Directions API. Returns (duration_mins, distance_km) or None.
    """
    key = api_key or _get_api_key()
    if not key or not origin or not destination:
        return None
    o = urllib.parse.quote_plus(origin.strip())
    d = urllib.parse.quote_plus(destination.strip())
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={o}&destination={d}&mode=transit&departure_time={departure_time_unix}&key={key}"
    try:
        data = _request_get(url)
        if data.get("status") != "OK" or not data.get("routes"):
            return None
        leg = data["routes"][0].get("legs", [{}])[0]
        dur = leg.get("duration", {}).get("value", 0)
        dist = leg.get("distance", {}).get("value", 0)
        return (dur / 60.0, dist / 1000.0)
    except Exception:
        return None


# ---------- Routes API (transit matrix) ----------


def _parse_duration_protobuf(s: str) -> float:
    """Parse protobuf duration string e.g. '123s' or '90.5s' to seconds."""
    if not s:
        return 0.0
    m = re.match(r"^(\d+(?:\.\d+)?)s$", s.strip())
    return float(m.group(1)) if m else 0.0


def routes_transit_matrix(
    origin: str,
    destinations: list[str],
    departure_time_rfc3339: str,
    api_key: str | None = None,
) -> list[tuple[float, float] | None]:
    """
    Get transit duration and distance from one origin to each destination.
    Uses Routes API computeRouteMatrix (travelMode=TRANSIT).
    departure_time_rfc3339: e.g. '2025-02-11T08:00:00Z'.
    Returns list of (duration_mins, distance_km) or None per destination.
    """
    key = api_key or _get_api_key()
    if not key or not origin or not destinations:
        return [None] * len(destinations)
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    body = {
        "origins": [{"waypoint": {"address": origin.strip()}}],
        "destinations": [{"waypoint": {"address": d.strip()}} for d in destinations],
        "travelMode": "TRANSIT",
        "departureTime": departure_time_rfc3339,
    }
    headers = {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "originIndex,destinationIndex,status,condition,distanceMeters,duration",
    }
    try:
        resp = _request_post(url, body, headers)
        # Response: list of element dicts (stream = one dict per line, or single JSON array)
        if isinstance(resp, list) and not resp:
            return [None] * len(destinations)
        if isinstance(resp, str):
            return [None] * len(destinations)
        elements = resp if isinstance(resp, list) else [resp]
        # Single JSON array: elements is [elem0, elem1, ...]; NDJSON: same
        if elements and not isinstance(elements[0], dict):
            return [None] * len(destinations)
        out: list[tuple[float, float] | None] = [None] * len(destinations)
        for el in elements:
            if not isinstance(el, dict):
                continue
            dest_idx = el.get("destinationIndex", 0)
            if dest_idx >= len(destinations):
                continue
            status = el.get("status") or {}
            if status.get("code") not in (0, None):
                continue
            cond = el.get("condition", "")
            if "ROUTE_NOT_FOUND" in str(cond):
                continue
            dur_s = _parse_duration_protobuf(el.get("duration") or "")
            dist_m = el.get("distanceMeters") or 0
            out[dest_idx] = (dur_s / 60.0, dist_m / 1000.0)
        return out
    except Exception:
        return [None] * len(destinations)


# ---------- Places: API (New) searchNearby, with legacy fallback ----------


def _places_nearby_legacy(
    lat: float,
    lng: float,
    radius_m: int,
    api_key: str,
) -> list[dict[str, Any]]:
    """Legacy Places API (GET nearbysearch). Used when Places API (New) returns no results."""
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    types = ["restaurant", "cafe", "park", "supermarket", "grocery_or_supermarket"]
    for t in types[:5]:
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lng}&radius={min(radius_m, 50000)}&type={t}&key={api_key}&language=en"
        )
        try:
            data = _request_get(url)
            if data.get("status") != "OK":
                continue
            for r in (data.get("results") or [])[:10]:
                name = (r.get("name") or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                results.append({
                    "name": name,
                    "types": r.get("types") or [],
                    "vicinity": r.get("vicinity") or "",
                })
        except Exception:
            continue
        time.sleep(0.15)
    return results


def places_nearby(
    lat: float,
    lng: float,
    radius_m: int = NEARBY_RADIUS_M,
    place_types: list[str] | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return places within radius_m of (lat, lng). Tries Places API (New) searchNearby first;
    if that returns no results (or errors), falls back to legacy Places API nearbysearch.
    Each item: {name, types, vicinity}.
    """
    key = api_key or _get_api_key()
    if not key:
        return []
    types = place_types or ["restaurant", "cafe", "park", "supermarket", "grocery_store"]
    url = "https://places.googleapis.com/v1/places:searchNearby"
    # Try without types first (all types) for best coverage; if empty, retry with specific types
    for included_types in (None, types[:10]):
        body = {
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(min(radius_m, 50000)),
                }
            },
        }
        if included_types:
            body["includedTypes"] = included_types
        headers = {
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "places.displayName,places.types,places.formattedAddress",
        }
        try:
            data = _request_post(url, body, headers)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    data = None
            if isinstance(data, list):
                places_list = data
            elif isinstance(data, dict):
                places_list = data.get("places") or []
            else:
                places_list = []
            if places_list:
                seen: set[str] = set()
                results: list[dict[str, Any]] = []
                for p in places_list:
                    if not isinstance(p, dict):
                        continue
                    name_obj = p.get("displayName") or {}
                    name = (name_obj.get("text") or "").strip() if isinstance(name_obj, dict) else ""
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    results.append({
                        "name": name,
                        "types": p.get("types") or [],
                        "vicinity": p.get("formattedAddress") or "",
                    })
                if results:
                    return results
        except Exception:
            pass
    # Fallback: legacy Places API (same key, often already enabled)
    return _places_nearby_legacy(lat, lng, radius_m, key)


# ---------- Helpers ----------


def next_weekday_9am_rfc3339() -> str:
    """Return RFC 3339 timestamp for next Tuesday 9:00 Berlin time (approximate)."""
    import datetime
    now = datetime.datetime.utcnow()
    days_ahead = (1 - now.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    tuesday = now + datetime.timedelta(days=days_ahead)
    # 8 UTC ≈ 9 Berlin in winter
    tuesday_8_utc = tuesday.replace(hour=8, minute=0, second=0, microsecond=0)
    return tuesday_8_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def next_weekday_9am_unix() -> int:
    """Return Unix timestamp for next Tuesday 9:00 local (Bremen). Used by Directions API."""
    import datetime
    now = datetime.datetime.utcnow()
    days_ahead = (1 - now.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    tuesday = now + datetime.timedelta(days=days_ahead)
    tuesday_9 = tuesday.replace(hour=8, minute=0, second=0, microsecond=0)
    return int(tuesday_9.timestamp())
