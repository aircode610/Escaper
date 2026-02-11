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

Extracted fields match the listings schema: `address`, `price_eur`, `rooms`, `description`, `raw` (JSON). The node fills `source`, `url`, `external_id` from the page.

---

## LangSmith tracing

To trace all agent and LLM calls in LangSmith:

1. **EU:** Sign up at [https://eu.smith.langchain.com](https://eu.smith.langchain.com) and create an API key.  
   **US:** Sign up at [https://smith.langchain.com](https://smith.langchain.com).

2. Add to `.env`:
   - `LANGCHAIN_TRACING_V2=true`
   - `LANGCHAIN_API_KEY=<your-key>`
   - `LANGSMITH_ENDPOINT` – **EU (default):** `https://eu.api.smith.langchain.com`  
     **US:** `https://api.smith.langchain.com`
   - `LANGCHAIN_PROJECT=escaper` (optional; default is `escaper`)

3. Run the agent as usual. Traces appear in your LangSmith dashboard (EU or US) under the project name.

**Important:** Env vars must be set *before* any langchain/langgraph import. The script `run_extract_one.py` does this by importing `config` and calling `config.setup_langsmith_tracing()` first. If you run the agent from other code, do the same (e.g. `import config; config.setup_langsmith_tracing()` before `from agent import ...`). If you set `LANGCHAIN_API_KEY` (or `LANGSMITH_API_KEY`), tracing is turned on automatically when not set.

---

## Running the agent

1. Set **`ANTHROPIC_API_KEY`** in `.env`.
2. Ensure you have at least one row in **listing_pages** (e.g. run `fetch_listing_pages --from-db --limit 5`).
3. From the **project root**:

```bash
# Run on the latest listing page in the DB
python scripts/run_extract_one.py
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
