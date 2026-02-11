"""
Extract main listing content or plain text from full page HTML.
Uses source-specific selectors when known, otherwise semantic tags or body.
"""

import re
from bs4 import BeautifulSoup


# Selectors to try per source (first match wins). First selector with enough text is used.
SOURCE_SELECTORS = {
    "immobilienscout24": ["main", "article", "#applicationHost", "#root", "#app", "[role='main']"],
    "kleinanzeigen": ["#main", "main", "article", "[role='main']"],
}


def extract_main_content(html: str | None, source: str | None = None) -> str | None:
    """
    Return only the main content HTML of a listing page.

    Args:
        html: Full page HTML.
        source: Optional site id (e.g. "immobilienscout24", "kleinanzeigen")
                 to use source-specific selectors.

    Returns:
        Extracted HTML string, or original html if extraction fails or no selector matches.
    """
    if not html or not html.strip():
        return html
    soup = BeautifulSoup(html, "html.parser")
    selectors = SOURCE_SELECTORS.get((source or "").lower(), []) if source else []
    # Generic selectors to try after source-specific
    selectors = selectors + ["main", "article", "[role='main']"]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 100:
            return str(el)
    # Fallback: body only, strip script/style to reduce size
    body = soup.find("body")
    if body:
        for tag in body.find_all(["script", "style"]):
            tag.decompose()
        return str(body)
    return html


def extract_text(html: str | None, source: str | None = None, main_content_only: bool = True) -> str | None:
    """
    Extract plain text from listing page HTML (no tags, minimal CSS noise).

    Args:
        html: Full page HTML.
        source: Optional site id for main-content selector hint.
        main_content_only: If True, narrow to main content first then get text (smaller, cleaner).

    Returns:
        Single string of normalized plain text, or None if no html.
    """
    if not html or not html.strip():
        return None
    if main_content_only:
        html = extract_main_content(html, source) or html
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style so they don't leak into text
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Normalize whitespace: collapse runs of spaces/newlines to single space
    text = re.sub(r"\s+", " ", text)
    return text.strip() or None
