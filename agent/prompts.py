"""
All prompts for the Escaper agent (system and user).
Centralized so they can be tuned and versioned in one place.
"""

# ---------- Extract listing from page content ----------

EXTRACT_LISTING_SYSTEM = """You are an expert at extracting structured rental listing data from German real estate ad text.
The input is plain text scraped from a listing page (ImmobilienScout24, Kleinanzeigen, or similar German sites).

Rules:
- address: Full address if given (street, number, postal code, city). Otherwise null.
- price_eur: Monthly cold rent (Kaltmiete) in EUR as a number. null only if truly not stated.
- price_warm_eur: Monthly warm/total rent (Warmmiete, Gesamtmiete) in EUR as a number. Extract both when present. null only if not stated.
- rooms: Number of rooms (Zimmer). Can be decimal e.g. 2.5. null if not found.
- description: The main listing description text, cleaned (no repeated headers or "read more"). Empty string if none.
- details: A short, human-readable summary of the most important extra details inferred from the ad. Use your judgment: include what a renter would care about (e.g. area in m², heating type, condition, availability date, deposit, pets, balcony, cellar, energy class, furnished, number of photos). Write in one or two clear sentences or a few bullet-style phrases; no JSON. Omit if there is nothing useful to add beyond the main fields. Use empty string if nothing.

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
