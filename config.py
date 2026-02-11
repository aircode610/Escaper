"""Load .env and expose API keys / config. Copy .env.example to .env and fill in values."""

import os

from dotenv import load_dotenv

load_dotenv()


def get_scrapfly_api_key() -> str | None:
    """ScrapFly API key for scraping. Required for scrapers."""
    return os.environ.get("SCRAPFLY_API_KEY") or None


def get_telegram_bot_token() -> str | None:
    """Telegram Bot token for notifications and user config."""
    return os.environ.get("TELEGRAM_BOT_TOKEN") or None


def get_google_maps_api_key() -> str | None:
    """Google Maps API key for distance calculations."""
    return os.environ.get("GOOGLE_MAPS_API_KEY") or None


def get_anthropic_api_key() -> str | None:
    """Anthropic (Claude) API key for scam detection."""
    return os.environ.get("ANTHROPIC_API_KEY") or None


# ---------- LangSmith tracing (agent) ----------
# https://docs.langchain.com/langsmith/observability-quickstart
# https://docs.langchain.com/langsmith/trace-with-langgraph


def get_langsmith_api_key() -> str | None:
    """LangSmith API key. Get one at EU: https://eu.smith.langchain.com | US: https://smith.langchain.com"""
    return os.environ.get("LANGSMITH_API_KEY") or None


def get_langsmith_endpoint() -> str:
    """LangSmith API endpoint. EU: https://eu.api.smith.langchain.com | US: https://api.smith.langchain.com"""
    return os.environ.get("LANGSMITH_ENDPOINT") or "https://eu.api.smith.langchain.com"


def is_langsmith_tracing_enabled() -> bool:
    """True if LangSmith tracing is enabled (LANGSMITH_TRACING=true)."""
    return os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1", "yes")


def get_langsmith_project() -> str:
    """Project name for LangSmith traces (default: escaper)."""
    return os.environ.get("LANGSMITH_PROJECT") or "escaper"


def setup_langsmith_tracing() -> None:
    """Load .env and set LANGSMITH_* / LANGCHAIN_* so LangSmith tracing works. Call before importing langchain/langgraph."""
    load_dotenv()
    api_key = get_langsmith_api_key()
    if api_key and not is_langsmith_tracing_enabled():
        os.environ["LANGSMITH_TRACING"] = "true"
    endpoint = get_langsmith_endpoint()
    if not os.environ.get("LANGSMITH_ENDPOINT"):
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
    project = get_langsmith_project()
    if not os.environ.get("LANGSMITH_PROJECT"):
        os.environ["LANGSMITH_PROJECT"] = project
    if is_langsmith_tracing_enabled():
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
    if not os.environ.get("LANGCHAIN_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    if not os.environ.get("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = project
