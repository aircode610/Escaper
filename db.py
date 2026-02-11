"""
SQLite storage for listings, listing URLs, and listing pages.
All tables use created_at DESC for latest-first ordering.
"""

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    external_id TEXT NOT NULL,
    address TEXT,
    price_eur REAL,
    price_warm_eur REAL,
    rooms REAL,
    description TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_external
ON listings (source, external_id);

CREATE TABLE IF NOT EXISTS listing_urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    external_id TEXT NOT NULL,
    city TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_listing_urls_external
ON listing_urls (source, external_id);

CREATE TABLE IF NOT EXISTS listing_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    external_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    content TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_listing_pages_external
ON listing_pages (source, external_id);
"""


DEFAULT_DB_PATH: str | Path = "data/listings.db"


def _get_conn(db_path: str | Path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(path))


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a connection for multiple operations. Caller must close/commit."""
    return _get_conn(db_path)


def _migrate_listings_add_price_warm(conn: sqlite3.Connection) -> None:
    """Add price_warm_eur column if missing (migration for existing DBs)."""
    cur = conn.execute("SELECT name FROM pragma_table_info('listings') WHERE name='price_warm_eur'")
    if cur.fetchone() is None:
        conn.execute("ALTER TABLE listings ADD COLUMN price_warm_eur REAL")
        conn.commit()


def _migrate_listings_raw_to_details(conn: sqlite3.Connection) -> None:
    """Rename raw_json to details, or add details column if missing."""
    cur = conn.execute("SELECT name FROM pragma_table_info('listings')")
    names = {row[0] for row in cur.fetchall()}
    if "raw_json" in names and "details" not in names:
        conn.execute("ALTER TABLE listings RENAME COLUMN raw_json TO details")
        conn.commit()
    elif "details" not in names:
        conn.execute("ALTER TABLE listings ADD COLUMN details TEXT")
        conn.commit()


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Create DB file and all tables (listings, listing_urls, listing_pages) if they don't exist."""
    conn = _get_conn(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        _migrate_listings_add_price_warm(conn)
        _migrate_listings_raw_to_details(conn)
    finally:
        conn.close()


def get_table_names(db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    """Return list of table names in the database."""
    conn = _get_conn(db_path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def get_table_row_count(conn: sqlite3.Connection, table: str) -> int:
    """Return row count for a table. Caller provides connection."""
    cur = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
    return cur.fetchone()[0]


def get_table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return column names for a table. Caller provides connection."""
    cur = conn.execute(f"PRAGMA table_info([{table}])")
    return [row[1] for row in cur.fetchall()]


def insert_listing(conn: sqlite3.Connection, row: dict) -> None:
    """Insert one listing (source, url, external_id; optional address, price_eur, price_warm_eur, rooms, description, details)."""
    conn.execute(
        """
        INSERT OR REPLACE INTO listings
        (source, url, external_id, address, price_eur, price_warm_eur, rooms, description, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.get("source"),
            row.get("url"),
            row.get("external_id"),
            row.get("address"),
            row.get("price_eur"),
            row.get("price_warm_eur"),
            row.get("rooms"),
            row.get("description"),
            row.get("details"),
        ),
    )


def row_to_listing(row: tuple) -> dict:
    """Convert a DB row (without id, created_at) to dict."""
    (
        source,
        url,
        external_id,
        address,
        price_eur,
        price_warm_eur,
        rooms,
        description,
        details,
    ) = row
    return {
        "source": source,
        "url": url,
        "external_id": external_id,
        "address": address,
        "price_eur": price_eur,
        "price_warm_eur": price_warm_eur,
        "rooms": rooms,
        "description": description,
        "details": details,
    }


def get_listings(
    db_path: str | Path = DEFAULT_DB_PATH,
    limit: int | None = None,
) -> list[dict]:
    """Return all listings sorted by latest date first (created_at DESC)."""
    conn = _get_conn(db_path)
    try:
        sql = """
        SELECT source, url, external_id, address, price_eur, price_warm_eur, rooms, description, details
        FROM listings
        ORDER BY created_at DESC
        """
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        cur = conn.execute(sql)
        return [row_to_listing(row) for row in cur.fetchall()]
    finally:
        conn.close()


# ---------- listing_urls ----------


def insert_listing_url(conn: sqlite3.Connection, row: dict) -> None:
    """Insert one listing URL (source, url, external_id; optional city). INSERT OR REPLACE by (source, external_id)."""
    conn.execute(
        """
        INSERT OR REPLACE INTO listing_urls (source, url, external_id, city)
        VALUES (?, ?, ?, ?)
        """,
        (
            row.get("source"),
            row.get("url"),
            row.get("external_id"),
            row.get("city"),
        ),
    )


def insert_listing_urls(conn: sqlite3.Connection, rows: list[dict], city: str | None = None) -> None:
    """Insert many listing URLs. Optional city stored for all rows."""
    for r in rows:
        if city is not None and "city" not in r:
            r = {**r, "city": city}
        insert_listing_url(conn, r)


def get_listing_urls(
    db_path: str | Path = DEFAULT_DB_PATH,
    city: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Return listing URLs (source, url, external_id, city), latest first. Optional city filter."""
    conn = _get_conn(db_path)
    try:
        sql = "SELECT source, url, external_id, city FROM listing_urls WHERE 1=1"
        params: list = []
        if city:
            sql += " AND city = ?"
            params.append(city)
        sql += " ORDER BY created_at DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        cur = conn.execute(sql, params)
        return [
            {"source": r[0], "url": r[1], "external_id": r[2], "city": r[3]}
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


# ---------- listing_pages ----------


def insert_listing_page(conn: sqlite3.Connection, row: dict) -> None:
    """Insert one listing page (source, url, external_id, content_type, content). INSERT OR REPLACE by (source, external_id)."""
    conn.execute(
        """
        INSERT OR REPLACE INTO listing_pages (source, url, external_id, content_type, content)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            row.get("source"),
            row.get("url"),
            row.get("external_id"),
            row.get("content_type"),
            row.get("content"),
        ),
    )


def insert_listing_pages(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Insert many listing pages."""
    for r in rows:
        insert_listing_page(conn, r)


def get_listing_pages(
    db_path: str | Path = DEFAULT_DB_PATH,
    limit: int | None = None,
) -> list[dict]:
    """Return listing pages (source, url, external_id, content_type, content), latest first."""
    conn = _get_conn(db_path)
    try:
        sql = """
        SELECT source, url, external_id, content_type, content
        FROM listing_pages
        ORDER BY created_at DESC
        """
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        cur = conn.execute(sql)
        return [
            {"source": r[0], "url": r[1], "external_id": r[2], "content_type": r[3], "content": r[4]}
            for r in cur.fetchall()
        ]
    finally:
        conn.close()
