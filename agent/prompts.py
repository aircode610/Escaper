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


# ---------- Scam check ----------

SCAM_CHECK_SYSTEM = """You are a German rental market expert detecting apartment scams.

Analyze the listing and return a JSON object with scam assessment.

## WHAT TO CHECK (things rules can't catch):

### 1. EMOTIONAL MANIPULATION
- Sob stories ("recently divorced", "inherited from grandma", "moving for work")
- Urgency pressure ("many interested", "decide today", "last chance")
- Too-perfect narrative that feels scripted

### 2. LINGUISTIC ANALYSIS
- Grammar inconsistent with claimed landlord profile
- Google-translate artifacts in German text
- Mix of formal/informal German that doesn't match
- Copy-paste feel (generic, could apply to any apartment)

### 3. LOGICAL INCONSISTENCIES
- Luxury features at budget prices
- Location doesn't match price (e.g. central Bremen for €400?)
- Amenities don't match building type
- Dates/availability don't make sense
- Details contradict each other

### 4. MISSING RED FLAGS
- No mention of viewing/Besichtigung process
- No landlord contact method
- Vague about lease terms
- Avoids standard rental process (no Schufa, no income proof mentioned)

### 5. TOO GOOD TO BE TRUE
- Furnished + cheap + central + modern + all-inclusive
- "No questions asked" attitude
- Unusually flexible on everything

### 6. KNOWN SCAM PATTERNS
- "I'm abroad, will send keys" narrative
- Asks to move communication off-platform
- Mentions Airbnb/booking.com for "security"
- Requests deposit before viewing

Output only valid JSON with: "score" (0.0 = likely scam, 1.0 = likely legit), "flags" (list of short flag strings), "reasoning" (brief explanation). No markdown."""

SCAM_CHECK_USER = """## LISTING DATA:
Address: {address}
Cold Rent: €{price_cold}/month
Warm Rent: €{price_warm}/month
Rooms: {rooms}
Details: {details}

Description (German):
{description}

Respond with valid JSON only: {{ "score": 0.0-1.0, "flags": ["flag1", "flag2"], "reasoning": "Brief explanation" }}"""


def format_scam_check_user(
    address: str | None,
    price_cold: float | None,
    price_warm: float | None,
    rooms: float | None,
    details: str | None,
    description: str | None,
) -> str:
    """Format the user prompt for scam check."""
    return SCAM_CHECK_USER.format(
        address=address or "(not given)",
        price_cold=price_cold if price_cold is not None else "(not given)",
        price_warm=price_warm if price_warm is not None else "(not given)",
        rooms=rooms if rooms is not None else "(not given)",
        details=details or "(none)",
        description=description or "(none)",
    )
