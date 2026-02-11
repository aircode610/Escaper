"""
Fetch full HTML for a list of listing URLs via fetch_listing_pages.
Reads URLs from the JSON file produced by fetch_listing_urls.py.

Usage:
  python scripts/fetch_listing_pages.py data/listing_urls.json
  python scripts/fetch_listing_pages.py data/listing_urls.json -o data/pages.json
  python scripts/fetch_listing_pages.py data/listing_urls.json --max-concurrent 10

Input: JSON array of {"source", "url", "external_id"} (from fetch_listing_urls).
Output: JSON array of {"source", "url", "external_id", "html"} or with --text {"source", "url", "external_id", "text"}.
By default only main content HTML is stored. Use --full for full HTML, or --text for plain text only (smallest).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
from scrapers.content import extract_main_content, extract_text  # noqa: E402
from scrapers.scraper import fetch_listing_pages  # noqa: E402

DEFAULT_OUTPUT = Path("data/listing_pages.json")


async def main():
    parser = argparse.ArgumentParser(description="Fetch full HTML for listing URLs")
    parser.add_argument("urls_file", help="JSON file with list of {source, url, external_id}")
    parser.add_argument("-o", "--output", default=None, help=f"Output JSON path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max concurrent requests (default: 5)")
    parser.add_argument("--full", action="store_true", help="Store full page HTML (default: store only main content)")
    parser.add_argument("--text", action="store_true", help="Store only extracted plain text (no HTML; smallest)")
    args = parser.parse_args()

    api_key = config.get_scrapfly_api_key()
    if not api_key:
        print("Set SCRAPFLY_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    urls_path = Path(args.urls_file)
    if not urls_path.is_file():
        print(f"File not found: {urls_path}", file=sys.stderr)
        sys.exit(1)

    with open(urls_path, encoding="utf-8") as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print("Expected JSON array of {source, url, external_id}", file=sys.stderr)
        sys.exit(1)

    urls = [e["url"] for e in entries if isinstance(e.get("url"), str)]
    if len(urls) != len(entries):
        print("Skipping entries without valid 'url'", file=sys.stderr)
    print(f"Fetching {len(urls)} pages (max_concurrent={args.max_concurrent}) ...", flush=True)

    done = 0
    failed = 0

    def on_fetched(u: str, success: bool) -> None:
        nonlocal done, failed
        done += 1
        if not success:
            failed += 1
        print(f"  [{done}/{len(urls)}] {'ok' if success else 'fail'}", flush=True)

    pages = await fetch_listing_pages(
        api_key,
        urls,
        max_concurrent=args.max_concurrent,
        on_page_fetched=on_fetched,
    )
    url_to_html = {p["url"]: p["html"] for p in pages}

    results = []
    for e in entries:
        if not isinstance(e.get("url"), str):
            continue
        html = url_to_html.get(e["url"])
        if args.text:
            text = extract_text(html, e.get("source"), main_content_only=True) if html else None
            results.append({
                "source": e.get("source"),
                "url": e["url"],
                "external_id": e.get("external_id"),
                "text": text,
            })
        else:
            if html and not args.full:
                html = extract_main_content(html, e.get("source"))
            results.append({
                "source": e.get("source"),
                "url": e["url"],
                "external_id": e.get("external_id"),
                "html": html,
            })

    out_path = Path(args.output) if args.output else DEFAULT_OUTPUT
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(results)} entries to {out_path} ({failed} failed)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
