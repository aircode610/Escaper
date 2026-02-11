"""
LangGraph state schema for the Escaper agent.
"""

from typing import Any

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    State passed between agent nodes.

    - listing_page: One row from listing_pages (source, url, external_id, content_type, content).
    - extracted: Extracted listing dict (address, price_eur, rooms, description, raw) for DB insert.
    - error: Error message if a step failed.
    """

    listing_page: dict[str, Any]
    extracted: dict[str, Any]
    error: str
