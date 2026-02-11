# Escaper – Agent (LangGraph)

The agent is a LangGraph workflow that processes listing pages and populates the **listings** table. All agent code and prompts live under **`agent/`**.

---

## Layout

| Path | Purpose |
|------|--------|
| `agent/prompts.py` | All prompts (system and user). Single place to edit copy. |
| `agent/state.py` | LangGraph state schema (`AgentState`). |
| `agent/nodes.py` | Graph nodes (e.g. `extract_listing_node`). |
| `agent/graph.py` | Builds the graph, compiles it, and exposes `run_on_listing_page`. |
| `agent/__init__.py` | Exports `app`, `build_graph`, `run_on_listing_page`, `AgentState`. |

---

## First node: extract listing

**Node:** `extract_listing`

- **Input (state):** `listing_page` – one row from `listing_pages` (`source`, `url`, `external_id`, `content`).
- **Behaviour:** Uses Claude (Anthropic) to extract structured fields from the page text, then inserts (or replaces) a row in **listings**.
- **Output (state):** `extracted` (the row written to DB), or `error` if something failed.

Extracted fields match the listings schema: `address`, `price_eur`, `price_warm_eur`, `rooms`, `description`, `details` (human-readable summary). The node fills `source`, `url`, `external_id` from the page.

---

## Second node: scam check

**Node:** `scam_check`

- **Input (state):** Runs after `extract_listing` when extraction succeeded (`extracted` set, no `error`).
- **Behaviour:** Uses Claude to assess the listing for scam indicators (emotional manipulation, linguistic issues, logical inconsistencies, missing red flags, too-good-to-be-true, known patterns). Returns a score 0.0–1.0 (0 = likely scam, 1 = likely legit), a list of flags, and brief reasoning.
- **Output (state):** `scam_score`, `scam_flags`, `scam_reasoning`; also updates the same listing row in the DB with these fields. On failure, sets `scam_error`.

Prompts are in `prompts.py` (`SCAM_CHECK_SYSTEM`, `SCAM_CHECK_USER`).

---

## Third node: enricher

**Node:** `enricher`

- **Input (state):** Runs after `scam_check`; uses `extracted` listing data.
- **Behaviour:**
  1. **Distances:** Google Maps Geocoding + Distance Matrix — walking and public transit (9am weekday) from listing address to Constructor University (Bremen) and to Bremen Hauptbahnhof.
  2. **Nearby places:** Places API (Nearby Search) — restaurants, cafes, parks, supermarkets within ~15 min walk (~1.2 km).
  3. **LLM:** Translates description to English (`description_en`), writes a short neighbourhood summary in English (`neighbourhood_vibe`), and assigns a value-for-money score 0–1 (`value_score`) given rent, size, and amenities.
- **Output:** Updates the listing row with all enrichment fields. Sets `enricher_error` on failure.

Requires **GOOGLE_MAPS_API_KEY** in `.env`. Enable in Google Cloud Console:
- **Geocoding API** — address → coordinates
- **Distance Matrix API** — walking times to university and HBF
- **Directions API** — transit fallback (one route per destination)
- **Routes API** — transit matrix (one request for all destinations)

Maps client: `agent/maps_client.py`. Test with `python scripts/test_maps_client.py`.

---

## LangSmith tracing

Follow the [Tracing quickstart](https://docs.langchain.com/langsmith/observability-quickstart) and [Trace with LangGraph](https://docs.langchain.com/langsmith/trace-with-langgraph):

1. **Sign up and create an API key**  
   EU: [https://eu.smith.langchain.com](https://eu.smith.langchain.com) · US: [https://smith.langchain.com](https://smith.langchain.com)

2. **Set in `.env`** (must be set *before* any langchain/langgraph import):
   - `LANGSMITH_TRACING=true`
   - `LANGSMITH_API_KEY=<your-langsmith-api-key>`
   - (optional) `LANGSMITH_PROJECT=escaper` — else traces go to project "default"
   - (optional) `LANGSMITH_WORKSPACE_ID=<id>` — if your API key is linked to multiple workspaces
   - **EU:** `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`

3. Run the agent. Call `config.setup_langsmith_tracing()` before importing the agent so env vars are set. Traces appear in your LangSmith project (EU or US).

---

## Running the agent

1. Set **`ANTHROPIC_API_KEY`** in `.env`.
2. Ensure you have rows in **listing_pages** (e.g. run `fetch_listing_pages --from-db --limit 5`).
3. From the **project root**:

```bash
# Process all listing pages in the DB (upserts into listings; table is never cleared)
python scripts/run_extract_one.py

# Process at most 10 pages
python scripts/run_extract_one.py --limit 10
```

Programmatic usage:

```python
from agent import run_on_listing_page

page = {"source": "immobilienscout24", "url": "https://...", "external_id": "123", "content": "..."}
result = run_on_listing_page(page)
# result["extracted"] = row written to listings; result["error"] = None or error message
```

---

## Prompts

All prompts are in **`agent/prompts.py`**:

- **`EXTRACT_LISTING_SYSTEM`** – System prompt for the extraction step (German rental ads, field rules, JSON-only output).
- **`EXTRACT_LISTING_USER`** – User prompt template (source, URL, ad text). Use **`format_extract_listing_user(source, url, content)`** to fill it.

Adding new nodes: define system/user prompts in `prompts.py`, then use them in the node in `nodes.py`.
