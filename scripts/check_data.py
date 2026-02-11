#!/usr/bin/env python3
"""
Print all data stored in data/ (SQLite listings and any other files).
Run from project root: python scripts/check_data.py
Uses only stdlib (sqlite3, json) so no need to install project deps.
"""

import json
import sqlite3
from pathlib import Path

# Path relative to project root
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "listings.db"


def main():
    if not DATA_DIR.exists():
        print(f"No data directory: {DATA_DIR}")
        return

    print(f"=== Contents of {DATA_DIR} ===\n")
    for f in sorted(DATA_DIR.iterdir()):
        if f.is_file():
            size = f.stat().st_size
            print(f"  {f.name}  ({size:,} bytes)")
    print()

    if not DB_PATH.exists():
        print("No listings.db found.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT id, source, url, external_id, address, price_eur, rooms,
                   description, raw_json, created_at
            FROM listings
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    print(f"=== Listings ({len(rows)} rows, latest first) ===\n")
    for row in rows:
        (
            id_,
            source,
            url,
            external_id,
            address,
            price_eur,
            rooms,
            description,
            raw_json,
            created_at,
        ) = row
        raw = json.loads(raw_json) if raw_json else None

        print("-" * 60)
        print(f"  id           {id_}")
        print(f"  source       {source}")
        print(f"  external_id  {external_id}")
        print(f"  created_at   {created_at}")
        print(f"  url          {url}")
        print(f"  address      {address or '-'}")
        print(f"  price_eur    {price_eur}")
        print(f"  rooms        {rooms}")
        if raw:
            print(f"  raw          {json.dumps(raw, ensure_ascii=False, indent=4)}")
        if description:
            print(f"  description  ({len(description)} chars)")
            print()
            for line in description.strip().split("\n")[:30]:
                print(f"    {line}")
            if len(description.strip().split("\n")) > 30:
                print("    ...")
            print()
        else:
            print(f"  description  (empty)")
        print()

    print("-" * 60)
    print(f"Total: {len(rows)} listing(s)")


if __name__ == "__main__":
    main()
