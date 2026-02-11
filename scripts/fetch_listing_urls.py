"""
Fetch listing URLs (and ids) from supported sites via Scrapfly.
Saves to the database (listing_urls table). Optionally export to JSON with -o.

Usage:
  python scripts/fetch_listing_urls.py [CITY]
  python scripts/fetch_listing_urls.py Bremen
  python scripts/fetch_listing_urls.py Berlin -o data/berlin_urls.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
import db  # noqa: E402
from scrapers.scraper import fetch_listing_urls  # noqa: E402

DEFAULT_JSON_OUTPUT = Path("data/listing_urls.json")


async def main():
    parser = argparse.ArgumentParser(description="Fetch listing URLs from supported sites")
    parser.add_argument("city", nargs="?", default="Bremen", help="City to search (default: Bremen)")
    parser.add_argument("-o", "--output", default=None, help="Optional: also write JSON to this path")
    args = parser.parse_args()

    api_key = config.get_scrapfly_api_key()
    if not api_key:
        print("Set SCRAPFLY_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    def log(name: str, url: str, count: int) -> None:
        print(f"[{name}] {url} -> {count} links", flush=True)

    results = await fetch_listing_urls(api_key, args.city, on_site_fetch=log)

    db.init_db()
    conn = db.get_connection()
    try:
        db.insert_listing_urls(conn, results, city=args.city)
        conn.commit()
    finally:
        conn.close()
    print(f"Saved {len(results)} entries to DB (listing_urls)")

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Also wrote JSON to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
