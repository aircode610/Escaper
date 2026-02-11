"""
LangGraph workflow for the Escaper agent.
LangSmith: set LANGSMITH_TRACING=true and LANGSMITH_API_KEY in .env to trace runs.
"""

import config  # noqa: E402

from langgraph.graph import END, START, StateGraph

from agent.nodes import extract_listing_node, enricher_node, scam_check_node, telegram_node
from agent.state import AgentState

config.setup_langsmith_tracing()


def _after_extract_route(state):
    """Route to scam_check when extraction succeeded, else END."""
    if state.get("extracted") and not state.get("error"):
        return "scam_check"
    return "__end__"


def build_graph():
    """Build and return the compiled agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("extract_listing", extract_listing_node)
    graph.add_node("scam_check", scam_check_node)
    graph.add_node("enricher", enricher_node)
    graph.add_node("telegram", telegram_node)

    graph.add_edge(START, "extract_listing")
    graph.add_conditional_edges("extract_listing", _after_extract_route, {"scam_check": "scam_check", "__end__": END})
    graph.add_edge("scam_check", "enricher")
    graph.add_edge("enricher", "telegram")
    graph.add_edge("telegram", END)

    return graph.compile()


app = build_graph()


def run_on_listing_page(listing_page: dict) -> dict:
    """Run the agent on one listing_page (source, url, external_id, content). Returns final state (extracted, error)."""
    initial: AgentState = {"listing_page": listing_page}
    return app.invoke(initial)
