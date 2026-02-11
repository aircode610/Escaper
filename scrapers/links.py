"""
Extract listing links from HTML: URL + external_id per link.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse_listing_links(
    html: str,
    base_url: str,
    link_contains: str,
    id_regex: str,
) -> list[dict]:
    """
    Find all <a href> that contain link_contains, normalize to full URL, extract id with id_regex.
    Returns list of {"url": str, "external_id": str}. Deduped by url.
    """
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(id_regex)
    seen: set[str] = set()
    out: list[dict] = []
    base = base_url.rstrip("/")

    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or link_contains not in href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full = urljoin(base_url, href)
        full = full.split("?")[0].split("#")[0].rstrip("/")
        if not full.startswith(("http://", "https://")):
            continue
        if full in seen:
            continue
        seen.add(full)
        match = pattern.search(full)
        if match:
            groups = match.groups()
            external_id = next((g for g in groups if g), full)
        else:
            external_id = full.replace(base, "").strip("/") or full
        out.append({"url": full, "external_id": external_id})

    return out
