#!/usr/bin/env python3
"""
Test the Google Maps client.
Run from project root: python scripts/test_maps_client.py

APIs used: Geocoding, Distance Matrix (walking), Directions (transit), Routes (transit).
Requires GOOGLE_MAPS_API_KEY in .env. Enable these in Google Cloud Console.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from agent.maps_client import (
    DEFAULT_HBF,
    DEFAULT_UNIVERSITY,
    directions_transit,
    distance_matrix,
    geocode,
    next_weekday_9am_rfc3339,
    next_weekday_9am_unix,
    routes_transit_matrix,
)


def _raw_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _print_api_error(api_name: str, data: dict) -> None:
    status = data.get("status", "?")
    msg = data.get("error_message", "")
    print(f"   Google response: status={status!r}")
    if msg:
        print(f"   error_message: {msg}")
    if status == "REQUEST_DENIED" and not msg:
        print("   (Enable the API in Google Cloud Console and check key restrictions.)")


def main():
    key = config.get_google_maps_api_key()
    if not key:
        print("ERROR: GOOGLE_MAPS_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    print("GOOGLE_MAPS_API_KEY is set (length {}).\n".format(len(key)))

    # 1) Geocode
    test_address = "Otto-Lilienthal-Straße 12, 28199 Bremen, Germany"
    print("1) Geocode:", test_address)
    try:
        coords = geocode(test_address)
        if coords:
            lat, lng = coords
            print(f"   OK -> lat={lat:.5f}, lng={lng:.5f}\n")
        else:
            print("   FAIL -> no result")
            q = urllib.parse.quote_plus(test_address)
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={q}&key={key}"
            try:
                data = _raw_get(url)
                _print_api_error("Geocoding", data)
            except Exception as e:
                print(f"   Request error: {e}")
            print()
    except Exception as e:
        print(f"   ERROR -> {e}\n")
        coords = None

    # 2) Distance matrix (walking)
    origin = test_address
    destinations = [DEFAULT_UNIVERSITY, DEFAULT_HBF]
    print("2) Distance matrix (walking)")
    print(f"   Origin: {origin[:50]}...")
    print(f"   Destinations: University, HBF")
    try:
        results = distance_matrix(origin, destinations, mode="walking")
        if results and (results[0] or results[1]):
            uni = results[0]
            hbf = results[1]
            print(f"   To University: {uni[0]:.0f} min, {uni[1]:.2f} km" if uni else "   To University: n/a")
            print(f"   To HBF:        {hbf[0]:.0f} min, {hbf[1]:.2f} km" if hbf else "   To HBF: n/a")
            print()
        else:
            print("   FAIL -> no results")
            o = urllib.parse.quote_plus(origin)
            d = urllib.parse.quote_plus("|".join(destinations))
            url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={o}&destinations={d}&mode=walking&key={key}"
            try:
                data = _raw_get(url)
                _print_api_error("Distance Matrix", data)
            except Exception as e:
                print(f"   Request error: {e}")
            print()
    except Exception as e:
        print(f"   ERROR -> {e}\n")

    # 3) Transit (Routes API, then Directions API fallback)
    print("3) Transit (Routes API, 9am weekday)")
    dep_rfc = next_weekday_9am_rfc3339()
    print(f"   Departure (RFC3339): {dep_rfc}")
    try:
        results = routes_transit_matrix(origin, destinations, dep_rfc)
        if results and (results[0] or results[1]):
            uni = results[0]
            hbf = results[1]
            print(f"   To University: {uni[0]:.0f} min" if uni else "   To University: n/a")
            print(f"   To HBF:        {hbf[0]:.0f} min" if hbf else "   To HBF: n/a")
            print("   (Routes API)\n")
        else:
            print("   Routes API -> no results, trying Directions API...")
            dep_unix = next_weekday_9am_unix()
            r1 = directions_transit(origin, DEFAULT_UNIVERSITY, dep_unix)
            r2 = directions_transit(origin, DEFAULT_HBF, dep_unix)
            if r1 or r2:
                print(f"   To University: {r1[0]:.0f} min" if r1 else "   To University: n/a")
                print(f"   To HBF:        {r2[0]:.0f} min" if r2 else "   To HBF: n/a")
                print("   (Directions API)\n")
            else:
                print("   FAIL -> no transit results\n")
    except Exception as e:
        print(f"   ERROR -> {e}\n")

    print("Done.")


if __name__ == "__main__":
    main()
