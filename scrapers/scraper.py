"""
Single entry point to scrape listing URLs and full listing pages.

Usage:
  from scrapers.scraper import fetch_listing_urls, fetch_listing_page, fetch_listing_pages

  urls = await fetch_listing_urls(api_key, "Bremen")
  html = await fetch_listing_page(api_key, urls[0]["url"])
  pages = await fetch_listing_pages(api_key, [u["url"] for u in urls[:5]])
"""

import asyncio
from typing import Callable

from scrapers.base import fetch
from scrapers.links import parse_listing_links
from scrapers.sites import SITES


def _slugify_city(city: str, style: str = "lower") -> str:
    if style == "title":
        return city.strip().title().replace(" ", "-")
    return city.strip().lower().replace(" ", "-")


async def fetch_listing_urls(
    api_key: str,
    city: str,
    *,
    on_site_fetch: Callable[[str, str, int], None] | None = None,
) -> list[dict]:
    """
    Fetch listing URLs (and external IDs) from all supported sites for one city.

    Args:
        api_key: Scrapfly API key.
        city: City name (e.g. "Bremen", "Berlin").
        on_site_fetch: Optional callback (site_name, search_url, link_count) after each site.

    Returns:
        List of {"source": str, "url": str, "external_id": str}.
    """
    results: list[dict] = []
    for site in SITES:
        base_url = site["base_url"].rstrip("/")
        slug = _slugify_city(city, site.get("city_slug", "lower"))
        search_url = base_url + site["search_path"].format(city=slug)

        html = await fetch(api_key, search_url)
        if not html:
            if on_site_fetch:
                on_site_fetch(site["name"], search_url, 0)
            continue
        links = parse_listing_links(
            html,
            base_url,
            site["link_contains"],
            site["id_regex"],
        )
        for item in links:
            results.append({
                "source": site["id"],
                "url": item["url"],
                "external_id": item["external_id"],
            })
        if on_site_fetch:
            on_site_fetch(site["name"], search_url, len(links))
    return results


def fetch_listing_urls_sync(api_key: str, city: str) -> list[dict]:
    """Synchronous wrapper for fetch_listing_urls."""
    return asyncio.run(fetch_listing_urls(api_key, city))


async def fetch_listing_page(api_key: str, url: str) -> str | None:
    """
    Fetch the full HTML of a single listing page.

    Args:
        api_key: Scrapfly API key.
        url: Full listing URL (e.g. from fetch_listing_urls).

    Returns:
        HTML string or None on failure.
    """
    return await fetch(api_key, url)


def fetch_listing_page_sync(api_key: str, url: str) -> str | None:
    """Synchronous wrapper for fetch_listing_page."""
    return asyncio.run(fetch_listing_page(api_key, url))


async def fetch_listing_pages(
    api_key: str,
    urls: list[str],
    *,
    max_concurrent: int = 5,
    on_page_fetched: Callable[[str, bool], None] | None = None,
) -> list[dict]:
    """
    Fetch full HTML for multiple listing URLs (concurrent, rate-limited).

    Args:
        api_key: Scrapfly API key.
        urls: List of listing URLs.
        max_concurrent: Max concurrent requests.
        on_page_fetched: Optional callback (url, success) after each page.

    Returns:
        List of {"url": str, "html": str | None} in same order as urls.
    """
    sem = asyncio.Semaphore(max_concurrent)

    async def get_one(u: str) -> dict:
        async with sem:
            html = await fetch(api_key, u)
            if on_page_fetched:
                on_page_fetched(u, html is not None)
            return {"url": u, "html": html}

    return await asyncio.gather(*(get_one(u) for u in urls))


def fetch_listing_pages_sync(
    api_key: str,
    urls: list[str],
    *,
    max_concurrent: int = 5,
) -> list[dict]:
    """Synchronous wrapper for fetch_listing_pages."""
    return asyncio.run(fetch_listing_pages(api_key, urls, max_concurrent=max_concurrent))
