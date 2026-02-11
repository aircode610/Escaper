"""
LangGraph nodes for the Escaper agent.
"""

import sys
from pathlib import Path

# Allow importing project modules when run from project root or as package
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import BaseModel, Field

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

import config
import db
from agent.prompts import (
    ENRICHER_SYSTEM,
    EXTRACT_LISTING_SYSTEM,
    SCAM_CHECK_SYSTEM,
    format_enricher_user,
    format_extract_listing_user,
    format_scam_check_user,
)
from agent.state import AgentState
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


# ---------- Structured output schemas ----------


class ExtractedListing(BaseModel):
    """Fields extracted from a listing page (for DB listings table)."""

    address: str | None = Field(default=None, description="Full address if given")
    price_eur: float | None = Field(default=None, description="Monthly cold rent (Kaltmiete) in EUR")
    price_warm_eur: float | None = Field(default=None, description="Monthly warm rent (Warmmiete) in EUR")
    rooms: float | None = Field(default=None, description="Number of rooms (e.g. 2.5)")
    description: str | None = Field(default=None, description="Main listing description text")
    details: str | None = Field(
        default=None,
        description="Short human-readable summary of important extra details (area, heating, condition, availability, deposit, pets, etc.). One or two sentences or bullet-style phrases. Empty string if nothing.",
    )


class ScamAssessment(BaseModel):
    """Scam check result (score 0=likely scam, 1=likely legit)."""

    score: float = Field(ge=0.0, le=1.0, description="0.0 = likely scam, 1.0 = likely legit")
    flags: list[str] = Field(default_factory=list, description="Short flag strings for issues found")
    reasoning: str = Field(default="", description="Brief explanation of the assessment")


class EnrichedOutput(BaseModel):
    """Enricher output: translation, neighbourhood summary, value score."""

    description_en: str = Field(default="", description="Description translated to English")
    neighbourhood_vibe: str = Field(default="", description="Short neighbourhood summary in English")
    value_score: float = Field(ge=0.0, le=1.0, description="Value for money 0-1")


# ---------- Node: extract one listing page and add to listings ----------


def _get_extract_llm():
    """Chat model with structured output (requires Claude Sonnet 4.5 or Opus 4.1+)."""
    api_key = config.get_anthropic_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
    model = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        api_key=api_key,
        temperature=0,
    )
    return model.with_structured_output(ExtractedListing, method="json_schema")


def extract_listing_node(state: AgentState) -> dict:
    """
    Take one listing_page from state, extract structured data with the LLM, and insert into listings table.
    Updates state with 'extracted' and clears 'error', or sets 'error' on failure.
    """
    page = state.get("listing_page")
    if not page:
        return {"error": "No listing_page in state", "extracted": None}

    source = page.get("source") or ""
    url = page.get("url") or ""
    external_id = page.get("external_id") or ""
    content = page.get("content") or ""

    if not content:
        conn = db.get_connection()
        try:
            db.insert_listing(
                conn,
                {
                    "source": source,
                    "url": url,
                    "external_id": external_id,
                    "address": None,
                    "price_eur": None,
                    "price_warm_eur": None,
                    "rooms": None,
                    "description": None,
                    "details": None,
                },
            )
            conn.commit()
        finally:
            conn.close()
        return {"extracted": {"source": source, "url": url, "external_id": external_id}, "error": None}

    try:
        llm = _get_extract_llm()
        messages = [
            SystemMessage(content=EXTRACT_LISTING_SYSTEM),
            HumanMessage(content=format_extract_listing_user(source=source, url=url, content=content)),
        ]
        out: ExtractedListing = llm.invoke(messages)
    except Exception as e:
        return {"extracted": None, "error": str(e)}

    row = {
        "source": source,
        "url": url,
        "external_id": external_id,
        "address": out.address,
        "price_eur": out.price_eur,
        "price_warm_eur": out.price_warm_eur,
        "rooms": out.rooms,
        "description": out.description or None,
        "details": out.details or None,
    }

    conn = db.get_connection()
    try:
        db.insert_listing(conn, row)
        conn.commit()
    except Exception as e:
        return {"extracted": None, "error": str(e)}
    finally:
        conn.close()

    return {"extracted": row, "error": None}


# ---------- Node: scam check and update listing ----------


def _get_scam_llm():
    """Chat model with structured output for scam assessment."""
    api_key = config.get_anthropic_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
    model = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        api_key=api_key,
        temperature=0,
    )
    return model.with_structured_output(ScamAssessment, method="json_schema")


def scam_check_node(state: AgentState) -> dict:
    """
    Run scam assessment on the extracted listing and update the listing row with scam_score, scam_flags, scam_reasoning.
    Runs only when state has 'extracted' and no 'error'. Updates state with scam_score, scam_flags, scam_reasoning.
    """
    if state.get("error"):
        return {}
    extracted = state.get("extracted")
    if not extracted:
        return {}

    source = extracted.get("source") or ""
    external_id = extracted.get("external_id") or ""
    address = extracted.get("address")
    price_cold = extracted.get("price_eur")
    price_warm = extracted.get("price_warm_eur")
    rooms = extracted.get("rooms")
    details = extracted.get("details")
    description = extracted.get("description")

    try:
        llm = _get_scam_llm()
        messages = [
            SystemMessage(content=SCAM_CHECK_SYSTEM),
            HumanMessage(
                content=format_scam_check_user(
                    address=address,
                    price_cold=price_cold,
                    price_warm=price_warm,
                    rooms=rooms,
                    details=details,
                    description=description,
                )
            ),
        ]
        out: ScamAssessment = llm.invoke(messages)
    except Exception as e:
        return {"scam_error": str(e), "scam_score": None, "scam_flags": None, "scam_reasoning": None}

    conn = db.get_connection()
    try:
        db.update_listing_scam(
            conn,
            source=source,
            external_id=external_id,
            score=out.score,
            flags=out.flags or [],
            reasoning=out.reasoning or "",
        )
        conn.commit()
    except Exception as e:
        return {"scam_error": str(e), "scam_score": out.score, "scam_flags": out.flags, "scam_reasoning": out.reasoning}
    finally:
        conn.close()

    return {
        "scam_score": out.score,
        "scam_flags": out.flags,
        "scam_reasoning": out.reasoning,
        "scam_error": None,
    }


# ---------- Node: enricher (Maps + LLM) ----------


def _get_enricher_llm():
    """Chat model with structured output for enricher."""
    api_key = config.get_anthropic_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
    model = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        api_key=api_key,
        temperature=0,
    )
    return model.with_structured_output(EnrichedOutput, method="json_schema")


def enricher_node(state: AgentState) -> dict:
    """
    Enrich listing: distances (university, HBF), translate to English, neighbourhood vibe, value score.
    Uses Google Maps (geocode, distance matrix, places) and LLM. Updates listing row with enrichment.
    """
    if state.get("error"):
        return {}
    extracted = state.get("extracted")
    if not extracted:
        return {}

    source = extracted.get("source") or ""
    external_id = extracted.get("external_id") or ""
    address = extracted.get("address")
    price_cold = extracted.get("price_eur")
    price_warm = extracted.get("price_warm_eur")
    rooms = extracted.get("rooms")
    details = extracted.get("details")
    description = extracted.get("description")

    # 1) Geocode
    origin_addr = address or "Bremen, Germany"
    coords = geocode(origin_addr)
    lat, lng = coords if coords else (None, None)

    # 2) Distances: walking (Distance Matrix API) and transit (Routes API, fallback Directions API)
    destinations = [DEFAULT_UNIVERSITY, DEFAULT_HBF]
    walk_results = distance_matrix(origin_addr, destinations, mode="walking") if origin_addr else [None, None]
    uni_walk = walk_results[0][0] if walk_results and walk_results[0] else None
    hbf_walk = walk_results[1][0] if len(walk_results) > 1 and walk_results[1] else None
    # Transit: try Routes API first, then Directions API (2 calls)
    dep_rfc3339 = next_weekday_9am_rfc3339()
    dep_unix = next_weekday_9am_unix()
    transit_results = routes_transit_matrix(origin_addr, destinations, dep_rfc3339) if origin_addr else [None, None]
    if not (transit_results and (transit_results[0] or transit_results[1])):
        transit_results = [
            directions_transit(origin_addr, destinations[0], dep_unix) if origin_addr else None,
            directions_transit(origin_addr, destinations[1], dep_unix) if origin_addr else None,
        ]
    uni_transit = transit_results[0][0] if transit_results and transit_results[0] else None
    hbf_transit = transit_results[1][0] if len(transit_results) > 1 and transit_results[1] else None

    # 3) LLM: translate, neighbourhood vibe, value score
    try:
        llm = _get_enricher_llm()
        messages = [
            SystemMessage(content=ENRICHER_SYSTEM),
            HumanMessage(
                content=format_enricher_user(
                    address=address,
                    price_cold=price_cold,
                    price_warm=price_warm,
                    rooms=rooms,
                    details=details,
                    description=description,
                    uni_walk_mins=uni_walk,
                    uni_transit_mins=uni_transit,
                    hbf_walk_mins=hbf_walk,
                    hbf_transit_mins=hbf_transit,
                )
            ),
        ]
        out: EnrichedOutput = llm.invoke(messages)
    except Exception as e:
        conn = db.get_connection()
        try:
            db.update_listing_enrichment(
                conn,
                source,
                external_id,
                dist_university_walk_mins=uni_walk,
                dist_university_transit_mins=uni_transit,
                dist_hbf_walk_mins=hbf_walk,
                dist_hbf_transit_mins=hbf_transit,
                nearby_places=[],
            )
            conn.commit()
        finally:
            conn.close()
        return {"enricher_error": str(e)}

    # 5) Persist
    conn = db.get_connection()
    try:
        db.update_listing_enrichment(
            conn,
            source,
            external_id,
            dist_university_walk_mins=uni_walk,
            dist_university_transit_mins=uni_transit,
            dist_hbf_walk_mins=hbf_walk,
            dist_hbf_transit_mins=hbf_transit,
            description_en=out.description_en or None,
            neighbourhood_vibe=out.neighbourhood_vibe or None,
            nearby_places=[],
            value_score=out.value_score,
        )
        conn.commit()
    except Exception as e:
        return {"enricher_error": str(e)}
    finally:
        conn.close()

    return {"enricher_error": None}
