"""
Fetch a URL with Scrapfly (ASP, JS, DE proxy). Returns HTML or None.
"""

from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient


async def fetch(api_key: str, url: str, **config_overrides) -> str | None:
    """Fetch URL with Scrapfly. Returns HTML content or None on failure."""
    config = ScrapeConfig(
        url=url,
        asp=True,
        render_js=True,
        country="de",
        **config_overrides,
    )
    try:
        client = ScrapflyClient(key=api_key)
        async for response in client.concurrent_scrape(scrape_configs=[config]):
            if isinstance(response, ScrapeApiResponse) and getattr(response, "scrape_result", None):
                content = response.scrape_result.get("content")
                if content:
                    return content
            return None
    except Exception:
        pass
    return None
