#!/usr/bin/env python3
"""
Print data from the Escaper SQLite database. List all tables or show rows from a specific table.
Uses only stdlib (sqlite3) so no need to install project deps.

Run from project root:
  python scripts/check_data.py              # list tables and row counts
  python scripts/check_data.py listings    # show rows from 'listings'
  python scripts/check_data.py listing_urls
  python scripts/check_data.py listing_pages
  python scripts/check_data.py listing_pages --limit 5
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Path relative to project root
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "listings.db"


def ensure_listings_has_price_warm(conn: sqlite3.Connection) -> None:
    """Add price_warm_eur to listings if missing (stdlib-only migration for old DBs)."""
    cur = conn.execute("SELECT name FROM pragma_table_info('listings') WHERE name='price_warm_eur'")
    if cur.fetchone() is None:
        conn.execute("ALTER TABLE listings ADD COLUMN price_warm_eur REAL")
        conn.commit()


def ensure_listings_has_details(conn: sqlite3.Connection) -> None:
    """Rename raw_json to details or add details column (stdlib-only migration)."""
    cur = conn.execute("SELECT name FROM pragma_table_info('listings')")
    names = {row[0] for row in cur.fetchall()}
    if "details" in names:
        return
    if "raw_json" in names:
        conn.execute("ALTER TABLE listings RENAME COLUMN raw_json TO details")
    else:
        conn.execute("ALTER TABLE listings ADD COLUMN details TEXT")
    conn.commit()


def get_table_names(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [row[0] for row in cur.fetchall()]


def get_row_count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
    return cur.fetchone()[0]


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info([{table}])")
    return [row[1] for row in cur.fetchall()]


def format_cell(value, max_len: int = 200) -> str:
    if value is None:
        return "-"
    s = str(value)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def show_table(conn: sqlite3.Connection, table: str, limit: int | None = None) -> None:
    columns = get_columns(conn, table)
    count = get_row_count(conn, table)
    sql = f"SELECT * FROM [{table}] ORDER BY 1"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    cur = conn.execute(sql)
    rows = cur.fetchall()

    print(f"=== {table} ({count} row(s), showing {len(rows)}) ===\n")
    if not rows:
        return

    # Header
    col_widths = [max(len(c), 12) for c in columns]
    header = "  ".join(c.ljust(col_widths[i]) for i, c in enumerate(columns))
    print(header)
    print("-" * len(header))

    for row in rows:
        parts = []
        for i, val in enumerate(row):
            cell = format_cell(val, max_len=80)
            if len(cell) > col_widths[i]:
                col_widths[i] = min(80, len(cell) + 2)
            parts.append(cell.ljust(col_widths[i]))
        print("  ".join(parts))

    if limit and count > limit:
        print(f"\n... and {count - limit} more row(s). Use --limit N to change.")


def show_listings_detail(conn: sqlite3.Connection, limit: int | None = None) -> None:
    """Pretty-print listings table (description truncated)."""
    sql = """
        SELECT id, source, url, external_id, address, price_eur, price_warm_eur, rooms,
               description, details, created_at
        FROM listings
        ORDER BY created_at DESC
        """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    cur = conn.execute(sql)
    rows = cur.fetchall()

    count = get_row_count(conn, "listings")
    print(f"=== listings ({count} row(s), showing {len(rows)}) ===\n")
    if not rows:
        return

    for row in rows:
        (
            id_,
            source,
            url,
            external_id,
            address,
            price_eur,
            price_warm_eur,
            rooms,
            description,
            details,
            created_at,
        ) = row
        print("-" * 60)
        print(f"  id             {id_}")
        print(f"  source         {source}")
        print(f"  external_id    {external_id}")
        print(f"  created_at     {created_at}")
        print(f"  url            {url}")
        print(f"  address        {address or '-'}")
        print(f"  price_eur      {price_eur}")
        print(f"  price_warm_eur {price_warm_eur}")
        print(f"  rooms          {rooms}")
        if details:
            print(f"  details        {details[:500]}{'...' if len(details) > 500 else ''}")
        if description:
            print(f"  description  ({len(description)} chars)")
            for line in description.strip().split("\n")[:15]:
                print(f"    {line}")
            if len(description.strip().split("\n")) > 15:
                print("    ...")
        else:
            print(f"  description  (empty)")
        print()

    if limit and count > limit:
        print(f"... and {count - limit} more row(s). Use --limit N to change.")


def main():
    parser = argparse.ArgumentParser(description="View Escaper DB tables and data")
    parser.add_argument("table", nargs="?", default=None, help="Table name (listings, listing_urls, listing_pages). Omit to list tables.")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to show for a table")
    parser.add_argument("--list", action="store_true", help="Only list table names and row counts (default when no table given)")
    args = parser.parse_args()

    if not DATA_DIR.exists():
        print(f"No data directory: {DATA_DIR}")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"No database at {DB_PATH}. Run fetch_listing_urls first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        tables = get_table_names(conn)
        if not tables:
            print("Database has no tables.")
            return

        if args.table is None or args.list:
            print("=== Tables ===\n")
            for t in tables:
                n = get_row_count(conn, t)
                print(f"  {t}: {n} row(s)")
            if args.table is None:
                print("\nUsage: python scripts/check_data.py <table> [--limit N]")
            return

        if args.table not in tables:
            print(f"Unknown table: {args.table}. Available: {', '.join(tables)}")
            sys.exit(1)

        if args.table == "listings":
            ensure_listings_has_price_warm(conn)
            ensure_listings_has_details(conn)
            show_listings_detail(conn, limit=args.limit)
        else:
            show_table(conn, args.table, limit=args.limit)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
