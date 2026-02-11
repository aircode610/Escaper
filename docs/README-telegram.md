# Telegram integration

After the enricher has run, the agent sends each listing to Telegram: a **compact message** in the chat and a **details file** attached.

---

## Pipeline

The graph runs in order:

1. **extract_listing** → 2. **scam_check** → 3. **enricher** → 4. **telegram** → END

The **telegram** node:

- Loads the listing from the DB (by `source` + `external_id` from state).
- Builds a short message (address, rent, rooms, distances, value score, link).
- Builds a text file with full details (description, neighbourhood vibe, scam assessment, etc.).
- Sends the message with `parse_mode=HTML`, then sends the file as `listing_details.txt`.

If `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` is missing, the node does nothing (no error). On failure it sets `telegram_error` in state.

---

## Setup

### 1. Bot token

1. Open Telegram and talk to [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, follow the prompts, and copy the **token** (e.g. `7123456789:AAH...`).
3. Put it in `.env`:

   ```env
   TELEGRAM_BOT_TOKEN=7123456789:AAH...
   ```

### 2. Chat ID

You need the chat (or channel) where the bot will post.

- **Private chat with the bot:** Start a chat with your bot, send any message. Then open:
  `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`  
  In the JSON, find `"chat":{"id":123456789,...}` — that number is your `TELEGRAM_CHAT_ID`.
- **Channel:** Add the bot as admin, then use the channel’s @username (e.g. `@mychannel`) or the numeric ID (e.g. `-1001234567890`) as `TELEGRAM_CHAT_ID`.

In `.env`:

```env
TELEGRAM_CHAT_ID=123456789
# or
TELEGRAM_CHAT_ID=@mychannel
```

---

## Env summary

| Variable              | Required | Description                          |
|-----------------------|----------|--------------------------------------|
| `TELEGRAM_BOT_TOKEN`  | Yes*     | Bot token from BotFather.            |
| `TELEGRAM_CHAT_ID`    | Yes*     | Chat or channel to send listings to. |

\*If either is missing, the telegram node is a no-op (no notification, no error).

---

## Message format

**In the chat (compact):**

- Address (bold)
- Cold / warm rent (€)
- Rooms
- Travel: Constructor Uni (walk + transit) and Bremen HBF (walk + transit)
- Value score (if present)
- Listing URL

**In the attached file (`listing_details.txt`):**

- Same basics plus: details summary, full description (English), neighbourhood vibe, scam score/flags/reasoning, value score, link.

---

## Running the pipeline

1. Fetch listing URLs and pages, then run the agent on each page (see main README or `docs/README-agent.md`). The agent runs **extract → scam_check → enricher → telegram**.
2. With Telegram configured, each successfully enriched listing is sent to `TELEGRAM_CHAT_ID` as soon as the enricher node finishes.

Example (single listing page):

```python
from agent import run_on_listing_page

result = run_on_listing_page({
    "source": "immoscout24",
    "url": "https://...",
    "external_id": "123",
    "content_type": "text/html",
    "content": "<html>...",
})
# If Telegram is configured:
# result.get("telegram_sent") == True  → message + file sent
# result.get("telegram_error")  → set if send failed
```

---

## Code

| Path                     | Purpose                                      |
|--------------------------|----------------------------------------------|
| `agent/telegram_client.py` | Build message/file and send via Bot API.   |
| `agent/nodes.py`         | `telegram_node`: load listing, call client.  |
| `agent/graph.py`         | Edge `enricher` → `telegram` → END.          |
| `config.py`              | `get_telegram_bot_token`, `get_telegram_chat_id`. |

Telegram is called over HTTPS ([Bot API](https://core.telegram.org/bots/api)) with `sendMessage` and `sendDocument`; no extra Python Telegram library is required.
