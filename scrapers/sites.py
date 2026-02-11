"""
Supported listing websites. Only IDs and URLs are scraped; all sites are city-based.

Each site: id, name, base_url, search_path, link_contains, id_regex, city_slug.
Placeholder in search_path: {city}.
"""

SITES = [
    {
        "id": "immobilienscout24",
        "name": "ImmobilienScout24",
        "base_url": "https://www.immobilienscout24.de",
        "search_path": "/Suche/de/{city}/wohnung-mieten",
        "link_contains": "/expose/",
        "id_regex": r"/expose/(\d+)",
        "city_slug": "lower",
    },
    {
        "id": "kleinanzeigen",
        "name": "Kleinanzeigen",
        "base_url": "https://www.kleinanzeigen.de",
        "search_path": "/s-wohnung-mieten/{city}/k0c203",
        "link_contains": "/s-anzeige/",
        "id_regex": r"/s-anzeige/[^/]+/(\d+)",
        "city_slug": "lower",
    },
]
