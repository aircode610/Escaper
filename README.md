# Escaper

*Because life's too short for bad housemates.*

Rental apartment finder agent: monitors German rental sites and sends Telegram notifications. Target user speaks English; sites are in German.

**Stack (planned):** LangGraph, Python 3.11+, Telegram Bot, Google Maps, Claude (scam detection), **ScrapFly** (scraping), SQLite.

**Data sources:** ImmobilienScout24, Kleinanzeigen, Rentola, Ferienwohnungen — all via ScrapFly for up-to-date, anti-bot–resistant scraping.

---

## Repo layout

```
Escaper/
  .gitignore
  README.md
  requirements.txt
  main.py
  docs/
    scrapfly-choice.md   # Why ScrapFly API vs MCP for this project
  scrapers/
    __init__.py
    schemas.py           # Listing dataclass
```

Scrapers (ImmobilienScout24 first) will be implemented next using the [ScrapFly API (Python SDK)](https://scrapfly.io/docs/sdk/python).

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys (at least SCRAPFLY_API_KEY for scraping)
```

API keys are loaded via `python-dotenv` from `.env`. See `.env.example` for required variables. Get a ScrapFly key at [scrapfly.io](https://scrapfly.io).
