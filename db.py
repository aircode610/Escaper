"""
Simple SQLite storage for listings. Sorted by latest first (created_at DESC).
"""

import json
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
    rooms REAL,
    description TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_external
ON listings (source, external_id);
"""


DEFAULT_DB_PATH: str | Path = "data/listings.db"


def _get_conn(db_path: str | Path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(path))


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a connection for multiple operations. Caller must close/commit."""
    return _get_conn(db_path)


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Create DB file and listings table if they don't exist."""
    conn = _get_conn(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_listing(conn: sqlite3.Connection, row: dict) -> None:
    """Insert one listing (dict with source, url, external_id; optional address, price_eur, rooms, description, raw)."""
    raw_json = json.dumps(row.get("raw"), ensure_ascii=False) if row.get("raw") else None
    conn.execute(
        """
        INSERT OR REPLACE INTO listings
        (source, url, external_id, address, price_eur, rooms, description, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.get("source"),
            row.get("url"),
            row.get("external_id"),
            row.get("address"),
            row.get("price_eur"),
            row.get("rooms"),
            row.get("description"),
            raw_json,
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
        rooms,
        description,
        raw_json,
    ) = row
    raw = json.loads(raw_json) if raw_json else None
    return {
        "source": source,
        "url": url,
        "external_id": external_id,
        "address": address,
        "price_eur": price_eur,
        "rooms": rooms,
        "description": description,
        "raw": raw,
    }


def get_listings(
    db_path: str | Path = DEFAULT_DB_PATH,
    limit: int | None = None,
) -> list[dict]:
    """Return all listings sorted by latest date first (created_at DESC)."""
    conn = _get_conn(db_path)
    try:
        sql = """
        SELECT source, url, external_id, address, price_eur, rooms, description, raw_json
        FROM listings
        ORDER BY created_at DESC
        """
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        cur = conn.execute(sql)
        return [row_to_listing(row) for row in cur.fetchall()]
    finally:
        conn.close()
