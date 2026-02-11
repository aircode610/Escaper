#!/usr/bin/env python3
"""
Run the extract-listing agent on one listing page from the DB (latest first).
Requires ANTHROPIC_API_KEY in .env. Run from project root: python scripts/run_extract_one.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
config.setup_langsmith_tracing()

import db
from agent import run_on_listing_page


def main():
    db.init_db()
    pages = db.get_listing_pages(limit=1)
    if not pages:
        print("No listing pages in DB. Run fetch_listing_pages first.", file=sys.stderr)
        sys.exit(1)
    page = pages[0]
    print(f"Running agent on: {page.get('source')} {page.get('external_id')} ...", flush=True)
    result = run_on_listing_page(page)
    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    print("Saved to listings:", result.get("extracted", {}).get("external_id"))


if __name__ == "__main__":
    main()
