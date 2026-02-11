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

**`scripts/fetch_listing_urls.py`** – Scrapes search pages for a city and saves all listing URLs and external IDs to the **database** (table `listing_urls`). Optionally export to JSON with `-o`.

```bash
python scripts/fetch_listing_urls.py                    # city Bremen → DB
python scripts/fetch_listing_urls.py Berlin              # city Berlin
python scripts/fetch_listing_urls.py Berlin -o data/berlin_urls.json   # also write JSON
```

**Output:** Saved to DB (`listing_urls`). Each row: `source`, `url`, `external_id`, `city`, `created_at`. With `-o`, also writes a JSON array of `{"source", "url", "external_id"}`.

---

### 2. Fetch listing pages

**`scripts/fetch_listing_pages.py`** – Fetches each listing page and saves HTML or text to the **database** (table `listing_pages`). URLs can come from a JSON file or from the DB (`--from-db`).

```bash
# From JSON file (e.g. exported with fetch_listing_urls -o)
python scripts/fetch_listing_pages.py data/listing_urls.json
python scripts/fetch_listing_pages.py data/listing_urls.json -o data/pages.json

# From DB (no file needed)
python scripts/fetch_listing_pages.py --from-db
python scripts/fetch_listing_pages.py --from-db --city Bremen --max-concurrent 10
```

**Output:** Saved to DB (`listing_pages`). Each row: `source`, `url`, `external_id`, `content_type` (`html` or `text`), `content`, `created_at`. Use `-o` to also export JSON.

| Mode | Flag | content_type | Description |
|------|------|--------------|-------------|
| Default | *(none)* | `html` | Main content HTML only |
| Full page | `--full` | `html` | Full page HTML |
| Text only | `--text` | `text` | Plain text only (smallest) |

For full DB schema and how to inspect data, see **[README-database.md](README-database.md)**.

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
