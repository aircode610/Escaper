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
from agent.prompts import EXTRACT_LISTING_SYSTEM, format_extract_listing_user
from agent.state import AgentState


# ---------- Structured output schema (matches listings table) ----------


class ExtractedListing(BaseModel):
    """Fields extracted from a listing page (for DB listings table)."""

    address: str | None = Field(default=None, description="Full address if given")
    price_eur: float | None = Field(default=None, description="Monthly cold rent in EUR")
    rooms: float | None = Field(default=None, description="Number of rooms (e.g. 2.5)")
    description: str | None = Field(default=None, description="Main listing description text")
    raw: dict | None = Field(default=None, description="Extra key-value pairs from the ad")


# ---------- Node: extract one listing page and add to listings ----------


def _get_extract_llm():
    api_key = config.get_anthropic_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
    model = ChatAnthropic(
        model="claude-sonnet-4-20250514",
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
                    "rooms": None,
                    "description": None,
                    "raw": None,
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
        "rooms": out.rooms,
        "description": out.description or None,
        "raw": out.raw,
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
