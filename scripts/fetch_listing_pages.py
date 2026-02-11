"""
Fetch full HTML (or text) for listing URLs and save to the database (listing_pages table).
Read URLs from a JSON file or from the DB (--from-db).

Usage:
  python scripts/fetch_listing_pages.py data/listing_urls.json
  python scripts/fetch_listing_pages.py --from-db [--city Bremen]
  python scripts/fetch_listing_pages.py --from-db --limit 5
  python scripts/fetch_listing_pages.py --from-db -o data/pages.json --max-concurrent 10

Input: JSON file or --from-db (optional --city). Use --limit N to fetch only the first N URLs (saves tokens).
Output: Saved to DB (listing_pages). Default = plain text only. Use --html/--full for HTML.
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
from scrapers.content import extract_main_content, extract_text  # noqa: E402
from scrapers.scraper import fetch_listing_pages  # noqa: E402

DEFAULT_JSON_OUTPUT = Path("data/listing_pages.json")


async def main():
    parser = argparse.ArgumentParser(description="Fetch full HTML for listing URLs and save to DB")
    parser.add_argument("urls_file", nargs="?", default=None, help="JSON file with list of {source, url, external_id}")
    parser.add_argument("--from-db", action="store_true", help="Read URLs from listing_urls table instead of a file")
    parser.add_argument("--city", default=None, help="When --from-db: only URLs for this city (default: all)")
    parser.add_argument("-o", "--output", default=None, help="Optional: also write JSON to this path")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max concurrent requests (default: 5)")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="Fetch only the first N URLs (saves API tokens; default: all)")
    parser.add_argument("--html", action="store_true", help="Store main-content HTML instead of plain text")
    parser.add_argument("--full", action="store_true", help="Store full page HTML (implies --html)")
    args = parser.parse_args()
    # Default: text mode. --html = main content HTML, --full = full page HTML
    store_html = args.html or args.full

    if args.from_db:
        if args.urls_file:
            print("Ignoring urls_file when --from-db is set.", file=sys.stderr)
        entries = db.get_listing_urls(city=args.city, limit=args.limit)
        if not entries:
            print("No listing URLs in DB" + (f" for city={args.city}" if args.city else ""), file=sys.stderr)
            sys.exit(1)
    else:
        if not args.urls_file:
            print("Provide urls_file or use --from-db", file=sys.stderr)
            sys.exit(1)
        urls_path = Path(args.urls_file)
        if not urls_path.is_file():
            print(f"File not found: {urls_path}", file=sys.stderr)
            sys.exit(1)
        with open(urls_path, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            print("Expected JSON array of {source, url, external_id}", file=sys.stderr)
            sys.exit(1)
        entries = raw
        if args.limit is not None:
            entries = entries[: args.limit]

    api_key = config.get_scrapfly_api_key()
    if not api_key:
        print("Set SCRAPFLY_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    urls = [e["url"] for e in entries if isinstance(e.get("url"), str)]
    if len(urls) != len(entries):
        print("Skipping entries without valid 'url'", file=sys.stderr)
    limit_note = f" (limit={args.limit})" if args.limit else ""
    print(f"Fetching {len(urls)} pages (max_concurrent={args.max_concurrent}){limit_note} ...", flush=True)

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
        if store_html:
            if html and not args.full:
                html = extract_main_content(html, e.get("source"))
            results.append({
                "source": e.get("source"),
                "url": e["url"],
                "external_id": e.get("external_id"),
                "content_type": "html",
                "content": html,
            })
        else:
            text = extract_text(html, e.get("source"), main_content_only=True) if html else None
            results.append({
                "source": e.get("source"),
                "url": e["url"],
                "external_id": e.get("external_id"),
                "content_type": "text",
                "content": text,
            })

    db.init_db()
    conn = db.get_connection()
    try:
        db.insert_listing_pages(conn, results)
        conn.commit()
    finally:
        conn.close()
    print(f"Saved {len(results)} entries to DB (listing_pages) ({failed} failed)", flush=True)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        export = []
        for r in results:
            row = {"source": r["source"], "url": r["url"], "external_id": r["external_id"]}
            if r["content_type"] == "text":
                row["text"] = r["content"]
            else:
                row["html"] = r["content"]
            export.append(row)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)
        print(f"Also wrote JSON to {out_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
