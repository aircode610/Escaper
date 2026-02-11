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
    EXTRACT_LISTING_SYSTEM,
    SCAM_CHECK_SYSTEM,
    format_extract_listing_user,
    format_scam_check_user,
)
from agent.state import AgentState


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
