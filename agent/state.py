"""
LangGraph state schema for the Escaper agent.
"""

from typing import Any

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    State passed between agent nodes.

    - listing_page: One row from listing_pages (source, url, external_id, content_type, content).
    - extracted: Extracted listing dict (address, price_eur, rooms, description, details) for DB insert.
    - error: Error message if a step failed.
    - scam_score, scam_flags, scam_reasoning: Set by scam_check node.
    - scam_error: Error message if scam check failed.
    - enricher_error: Error message if enricher node failed.
    """

    listing_page: dict[str, Any]
    extracted: dict[str, Any]
    error: str
    scam_score: float
    scam_flags: list[str]
    scam_reasoning: str
    scam_error: str
    enricher_error: str
