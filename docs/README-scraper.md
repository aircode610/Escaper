# Escaper – Scraper

Fetch listing **URLs and IDs** from supported sites via Scrapfly, then optionally fetch **full listing pages** (HTML or plain text). No structured parsing of price, rooms, or description beyond link extraction and optional text extraction.

---

## Supported websites

Defined in **`scrapers/sites.py`**:

| ID | Site |
|----|------|
| immobilienscout24 | ImmobilienScout24 (immobilienscout24.de) |
| kleinanzeigen | Kleinanzeigen (kleinanzeigen.de) |

Each entry has: `base_url`, `search_path` (with `{city}`), `link_contains`, `id_regex`, `city_slug` for building search URLs and extracting listing links.

---

## Setup

1. Copy `.env.example` to `.env` and set `SCRAPFLY_API_KEY`.
2. `pip install -r requirements.txt`

---

## Scripts

### 1. Fetch listing URLs

**`scripts/fetch_listing_urls.py`** – Scrapes search pages for a city and saves all listing URLs and external IDs.

```bash
python scripts/fetch_listing_urls.py                    # city Bremen → data/listing_urls.json
python scripts/fetch_listing_urls.py Berlin               # city Berlin
python scripts/fetch_listing_urls.py Berlin -o data/berlin_urls.json   # custom output path
```

**Output:** JSON file (default `data/listing_urls.json`) with an array of:

```json
{"source": "immobilienscout24", "url": "https://...", "external_id": "..."}
```

---

### 2. Fetch listing pages

**`scripts/fetch_listing_pages.py`** – Takes the URLs JSON from step 1, fetches each listing page, and saves HTML or plain text.

```bash
python scripts/fetch_listing_pages.py data/listing_urls.json
python scripts/fetch_listing_pages.py data/listing_urls.json -o data/listing_pages.json
python scripts/fetch_listing_pages.py data/listing_urls.json --max-concurrent 10
```

**Output:** JSON file (default `data/listing_pages.json`).

| Mode | Flag | Stored field | Description |
|------|------|--------------|-------------|
| Default | *(none)* | `html` | Main content HTML only (smaller than full page) |
| Full page | `--full` | `html` | Full page HTML |
| Text only | `--text` | `text` | Plain text only (smallest; no HTML) |

Examples:

```bash
# Main content HTML (default)
python scripts/fetch_listing_pages.py data/listing_urls.json

# Full page HTML
python scripts/fetch_listing_pages.py data/listing_urls.json --full

# Plain text only (smallest file)
python scripts/fetch_listing_pages.py data/listing_urls.json --text -o data/listing_text.json
```

**Output shape:**

- With HTML: `{"source", "url", "external_id", "html"}` (`html` is `null` on fetch failure).
- With `--text`: `{"source", "url", "external_id", "text"}` (`text` is `null` on failure).

---

## Programmatic usage

### Scraper (`scrapers.scraper`)

- **`fetch_listing_urls(api_key, city, *, on_site_fetch=None)`** (async) – Returns list of `{"source", "url", "external_id"}` for the city.
- **`fetch_listing_urls_sync(api_key, city)`** – Sync wrapper.
- **`fetch_listing_page(api_key, url)`** (async) – Fetches one listing URL; returns full HTML or `None`.
- **`fetch_listing_page_sync(api_key, url)`** – Sync wrapper.
- **`fetch_listing_pages(api_key, urls, *, max_concurrent=5, on_page_fetched=None)`** (async) – Fetches many URLs; returns list of `{"url", "html"}`.
- **`fetch_listing_pages_sync(api_key, urls, *, max_concurrent=5)`** – Sync wrapper.

### Content extraction (`scrapers.content`)

- **`extract_main_content(html, source=None)`** – Returns only the main content HTML (uses source-specific selectors, then `<main>` / `<article>`, then `<body>` with script/style removed).
- **`extract_text(html, source=None, main_content_only=True)`** – Returns plain text: strips tags, normalizes whitespace; optionally narrows to main content first.

Example:

```python
from scrapers import fetch_listing_urls, fetch_listing_pages, extract_text

urls = await fetch_listing_urls(api_key, "Bremen")
listing_url_list = [u["url"] for u in urls[:5]]
pages = await fetch_listing_pages(api_key, listing_url_list)
for p in pages:
    text = extract_text(p["html"], source="immobilienscout24")
    print(p["url"], "->", (text or "")[:200])
```

---

## Module layout

| Path | Role |
|------|------|
| `scrapers/sites.py` | Supported sites config (id, base_url, search_path, link_contains, id_regex, city_slug). |
| `scrapers/base.py` | Single `fetch(api_key, url)` via Scrapfly (ASP, JS, DE proxy). |
| `scrapers/links.py` | `parse_listing_links(html, base_url, link_contains, id_regex)` → list of `{url, external_id}`. |
| `scrapers/content.py` | `extract_main_content(html, source)`, `extract_text(html, source, main_content_only)`. |
| `scrapers/scraper.py` | `fetch_listing_urls`, `fetch_listing_page`, `fetch_listing_pages` (and sync variants). |
