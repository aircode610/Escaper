"""
LangGraph workflow for the Escaper agent.
"""

from langgraph.graph import END, START, StateGraph

from agent.nodes import extract_listing_node
from agent.state import AgentState


def build_graph():
    """Build and return the compiled agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("extract_listing", extract_listing_node)

    graph.add_edge(START, "extract_listing")
    graph.add_edge("extract_listing", END)

    return graph.compile()


# Compiled graph instance (call build_graph() to get a fresh one if needed)
app = build_graph()


def run_on_listing_page(listing_page: dict) -> dict:
    """
    Run the agent on one listing_page (source, url, external_id, content).
    Returns the final state (extracted, error).
    """
    initial: AgentState = {
        "listing_page": listing_page,
    }
    result = app.invoke(initial)
    return result
