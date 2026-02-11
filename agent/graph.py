"""
LangGraph workflow for the Escaper agent.
LangSmith tracing: set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env to trace all runs.
"""

import os

from langgraph.graph import END, START, StateGraph

from agent.nodes import extract_listing_node
from agent.state import AgentState

# Ensure .env is loaded and LangSmith defaults (EU endpoint, project "escaper")
import config  # noqa: E402
if not os.environ.get("LANGCHAIN_PROJECT") and not os.environ.get("LANGCHAIN_PROJECT_NAME"):
    os.environ.setdefault("LANGCHAIN_PROJECT", "escaper")
if not os.environ.get("LANGCHAIN_ENDPOINT"):
    os.environ.setdefault("LANGCHAIN_ENDPOINT", config.get_langsmith_endpoint())


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
    LangSmith: set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env to trace all runs.
    """
    initial: AgentState = {
        "listing_page": listing_page,
    }
    result = app.invoke(initial)
    return result
