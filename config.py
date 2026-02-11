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
