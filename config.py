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


def get_langsmith_api_key() -> str | None:
    """LangSmith API key for tracing. EU: https://eu.smith.langchain.com | US: https://smith.langchain.com"""
    return os.environ.get("LANGCHAIN_API_KEY") or os.environ.get("LANGSMITH_API_KEY") or None


def get_langsmith_endpoint() -> str:
    """LangSmith API endpoint. Defaults to EU (eu.api.smith.langchain.com). US: https://api.smith.langchain.com"""
    return (
        os.environ.get("LANGCHAIN_ENDPOINT")
        or os.environ.get("LANGSMITH_ENDPOINT")
        or "https://eu.api.smith.langchain.com"
    )


def is_langsmith_tracing_enabled() -> bool:
    """True if LangSmith tracing is enabled via LANGCHAIN_TRACING_V2=true."""
    return os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes")


def get_langsmith_project() -> str:
    """Project name for LangSmith traces (default: escaper)."""
    return os.environ.get("LANGCHAIN_PROJECT") or os.environ.get("LANGCHAIN_PROJECT_NAME") or "escaper"
