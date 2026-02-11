# Escaper

*Because life's too short for bad housemates.*

Rental apartment finder: monitors German rental sites, enriches listings (distances, scam check, translation), and sends compact Telegram notifications. Target user speaks English; sites are in German.

**Stack:** Python 3.11+, LangGraph, SQLite, ScrapFly (scraping), Google Maps (distances), Claude (extraction + scam detection), Telegram Bot API.

**Data sources:** ImmobilienScout24, Kleinanzeigen, Rentola, Ferienwohnungen — via ScrapFly for anti-bot–resistant scraping.

---

## Repo layout

```
Escaper/
  README.md
  requirements.txt
  main.py              # Entry: fetch listing URLs (ScrapFly)
  config.py            # .env / API keys
  db.py                # SQLite: listings, listing_urls, listing_pages
  agent/               # LangGraph pipeline
    graph.py           # extract → scam_check → enricher → telegram
    nodes.py           # Node implementations
    state.py           # AgentState
    prompts.py         # LLM prompts
    maps_client.py     # Geocoding, distance matrix, transit
    telegram_client.py # Format + send message + details file
  scrapers/
    base.py, content.py, links.py, scraper.py, sites.py
  scripts/
    fetch_listing_urls.py   # ScrapFly: discover listing URLs
    fetch_listing_pages.py  # ScrapFly: fetch page HTML → listing_pages
    run_extract_one.py      # Run agent on one page (extract → … → telegram)
    check_data.py           # DB migrations + listing summary
    test_maps_client.py     # Test Google Maps client
  docs/
    README-agent.md    # Agent nodes and graph
    README-database.md # Schema and DB usage
    README-scraper.md  # Scrapers and ScrapFly
    README-telegram.md # Telegram setup and pipeline
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: at least SCRAPFLY_API_KEY; optional: GOOGLE_MAPS_API_KEY, ANTHROPIC_API_KEY, TELEGRAM_*
```

API keys are loaded from `.env` via `python-dotenv`. See `.env.example` for all variables.

| Variable | Purpose |
|----------|---------|
| `SCRAPFLY_API_KEY` | **Required** for scraping (fetch URLs, fetch pages). [scrapfly.io](https://scrapfly.io) |
| `GOOGLE_MAPS_API_KEY` | Enricher: geocode + walking/transit times to Uni and HBF. |
| `ANTHROPIC_API_KEY` | Extract + scam check + enricher (Claude). |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Optional: send listing message + details file after enrich. |

---

## Pipeline

1. **Fetch listing URLs** (e.g. by city) → stored in `listing_urls`.
2. **Fetch listing pages** (HTML) → stored in `listing_pages`.
3. **Run agent** on each page: **extract** → **scam_check** → **enricher** → **telegram** (if configured). Writes/updates `listings`.

```bash
# 1) Get URLs (e.g. Bremen)
python main.py
# or: python scripts/fetch_listing_urls.py

# 2) Fetch pages from DB
python scripts/fetch_listing_pages.py --from-db

# 3) Run agent on stored pages (extract, scam, enrich, telegram)
python scripts/run_extract_one.py
# optional: --limit N
```

Details: **`docs/README-agent.md`** (graph and nodes), **`docs/README-telegram.md`** (notifications), **`docs/README-database.md`** (schema).
