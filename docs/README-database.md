# Escaper – Database

SQLite database for listings, listing URLs, and listing pages. File: **`data/listings.db`** (created on first use). Schema and helpers live in **`db.py`**.

---

## Database structure

### Tables overview

| Table | Purpose |
|-------|--------|
| **listings** | Parsed listings (address, price, rooms, description, raw JSON). One row per listing per (source, external_id). |
| **listing_urls** | Raw listing URLs and IDs from search-page scraping. Written by `fetch_listing_urls.py`; read by `fetch_listing_pages.py --from-db`. |
| **listing_pages** | Fetched HTML or plain text for each listing URL. Written by `fetch_listing_pages.py`. |

All tables have `created_at` and use **latest-first** ordering (DESC).

---

### Table: `listings`

Parsed/structured listing data (e.g. for notifications or downstream processing).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, auto-increment. |
| `source` | TEXT | Site id (e.g. `immobilienscout24`, `kleinanzeigen`). |
| `url` | TEXT | Full listing URL. |
| `external_id` | TEXT | ID on the source site. |
| `address` | TEXT | Parsed address (optional). |
| `price_eur` | REAL | Monthly rent in EUR (optional). |
| `rooms` | REAL | Number of rooms (optional). |
| `description` | TEXT | Listing description (optional). |
| `raw_json` | TEXT | JSON blob of raw extracted data (optional). |
| `created_at` | TEXT | Insert/update time, `datetime('now')`. |

**Unique index:** `(source, external_id)` — same listing is updated in place (INSERT OR REPLACE).

---

### Table: `listing_urls`

URLs and external IDs discovered from search pages. One row per (source, external_id) per city run.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, auto-increment. |
| `source` | TEXT | Site id. |
| `url` | TEXT | Full listing URL. |
| `external_id` | TEXT | ID on the source site. |
| `city` | TEXT | City used for the search (optional). |
| `created_at` | TEXT | Insert/update time. |

**Unique index:** `(source, external_id)` — repeated runs replace existing row.

---

### Table: `listing_pages`

Fetched page content (HTML or text) for each listing URL.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, auto-increment. |
| `source` | TEXT | Site id. |
| `url` | TEXT | Full listing URL. |
| `external_id` | TEXT | ID on the source site. |
| `content_type` | TEXT | `'html'` or `'text'`. |
| `content` | TEXT | Full HTML or plain text (can be large). |
| `created_at` | TEXT | Insert/update time. |

**Unique index:** `(source, external_id)` — re-fetching the same listing overwrites the row.

---

## Script: `check_data.py`

**`scripts/check_data.py`** inspects the database: list tables and row counts, or show rows from a specific table. Uses only Python stdlib (no project deps).

Run from project root:

```bash
# List all tables and row counts
python scripts/check_data.py

# Show rows from a table (latest first)
python scripts/check_data.py listings
python scripts/check_data.py listing_urls
python scripts/check_data.py listing_pages

# Limit number of rows
python scripts/check_data.py listing_pages --limit 5
python scripts/check_data.py listings --limit 10
```

**Behavior:**

- **No arguments:** Prints each table name and its row count, plus a short usage hint.
- **`<table>`:** Prints rows from that table. For `listings`, uses a detailed format (description/raw truncated). For `listing_urls` and `listing_pages`, prints a compact table; long values (e.g. `content`) are truncated.
- **`--limit N`:** Show at most N rows for the chosen table.

**Examples:**

```bash
python scripts/check_data.py
# === Tables ===
#   listing_pages: 42 row(s)
#   listing_urls: 100 row(s)
#   listings: 0 row(s)

python scripts/check_data.py listing_urls --limit 3
# === listing_urls (100 row(s), showing 3) ===
# id   source   url   external_id   city    created_at
# ...
```

The database path is fixed: **`data/listings.db`** (relative to project root). The `data/` directory is created by the fetch scripts when they first write to the DB.
