#!/usr/bin/env python3
"""
Run the extract-listing agent on listing pages from the DB (latest first).
Listings are upserted (INSERT OR REPLACE by source + external_id); the table is never cleared.

Requires ANTHROPIC_API_KEY in .env. Run from project root:
  python scripts/run_extract_one.py           # process all pages
  python scripts/run_extract_one.py --limit 5  # process 5 pages
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
config.setup_langsmith_tracing()

import db
from agent import run_on_listing_page


def main():
    parser = argparse.ArgumentParser(description="Extract listings from listing_pages and upsert into listings table")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N listing pages (default: all)",
    )
    args = parser.parse_args()

    db.init_db()
    pages = db.get_listing_pages(limit=args.limit)
    if not pages:
        print("No listing pages in DB. Run fetch_listing_pages first.", file=sys.stderr)
        sys.exit(1)

    ok = 0
    err = 0
    for i, page in enumerate(pages, 1):
        source = page.get("source") or ""
        ext_id = page.get("external_id") or ""
        print(f"[{i}/{len(pages)}] {source} {ext_id} ...", flush=True)
        result = run_on_listing_page(page)
        if result.get("error"):
            print(f"  Error: {result['error']}", file=sys.stderr)
            err += 1
        else:
            print(f"  Saved.", flush=True)
            ok += 1

    print(f"\nDone: {ok} saved, {err} failed.", flush=True)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
