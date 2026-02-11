"""Escaper – fetch listing URLs from supported sites via Scrapfly."""

import sys
from pathlib import Path

# Run the fetch script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scripts.fetch_listing_urls import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
