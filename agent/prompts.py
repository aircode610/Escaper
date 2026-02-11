"""
All prompts for the Escaper agent (system and user).
Centralized so they can be tuned and versioned in one place.
"""

# ---------- Extract listing from page content ----------

EXTRACT_LISTING_SYSTEM = """You are an expert at extracting structured rental listing data from German real estate ad text.
The input is plain text scraped from a listing page (ImmobilienScout24, Kleinanzeigen, or similar German sites).
Extract every relevant field you can find. Use null for any field that is not mentioned or cannot be determined.
Rules:
- address: Full address if given (street, number, postal code, city). Otherwise null.
- price_eur: Monthly cold rent (Kaltmiete) in EUR as a number. Ignore Nebenkosten or warm rent unless cold is missing. null if not found.
- rooms: Number of rooms (Zimmer). Can be decimal e.g. 2.5 for 2.5 Zimmer. null if not found.
- description: The main listing description text, cleaned (no repeated headers or "read more"). Empty string if none.
- raw: A JSON object with any extra useful key-value pairs you find (e.g. area_sqm, available_from, floor, heating_type). Use null if nothing extra.
Output only valid JSON matching the schema. No markdown or explanation."""

EXTRACT_LISTING_USER = """Extract the rental listing data from this ad text.

Source: {source}
URL: {url}

--- Ad text ---
{content}
--- End ---"""


def format_extract_listing_user(source: str, url: str, content: str) -> str:
    """Format the user prompt for listing extraction."""
    return EXTRACT_LISTING_USER.format(
        source=source,
        url=url,
        content=content or "(no content)",
    )
