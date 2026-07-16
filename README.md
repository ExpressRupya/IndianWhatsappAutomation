# Indian Datacenter News Automation

Daily Indian data centre news scraper — sends individual image cards + summary digest to WhatsApp.

## How it works

1. **Scrape** — Fetches news from SerpApi Google News using 10 targeted queries (CtrlS, AWS, Hyperscalers, Land Acquisition, etc.)
2. **Score & Prioritize** — Matches against 40 Indian DC companies. Boosts scores for Indian operators (CtrlS, Sify, Pi Datacentres, Bharti Airtel, TATA, NTT, etc.) then India-presence (AWS India, Google Cloud, Microsoft), then global.
3. **Deduplicate** — Removes same-story-from-different-sources using multi-angle fuzzy matching + key term extraction (co. names, cities, investment amounts, action words).
4. **24h Window** — Only articles published within the last 24 hours.
5. **Top-N Selection** — Picks the 15 highest-scoring articles by default.
6. **Image Cards** — For each article: fetches OG image from source URL (with text overlay) or generates a dark-themed Pillow card with Express logo, title, company, category badge, source, and snippet.
7. **Send** — Delivers 15 individual messages (image + summary) to WhatsApp, followed by one formatted summary digest.

## Setup

```bash
git clone https://github.com/ExpressRupya/IndianWhatsappAutomation.git
cd IndianWhatsappAutomation
```

### Environment (`.env`)

```
SERPAPI_KEY=your_serpapi_key
MIN_SCORE=20
MAX_ARTICLES=15
MAX_SEND_MESSAGES=0
WHATSAPP_COMMUNITY_NAME=ExpressNews
WHATSAPP_TARGET_CHAT_ID=120363410375552266@g.us
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

### Install & run

```bash
startup.bat
```

Or manually:

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
npm install
set MAX_ARTICLES=15
set MAX_SEND_MESSAGES=0
venv\Scripts\python run_daily.py
```

First run requires WhatsApp QR authentication via `setup_whatsapp.js`.

### Testing with 1 message

```bash
set MAX_ARTICLES=15
set MAX_SEND_MESSAGES=1
venv\Scripts\python run_daily.py
```

## Project structure

```
app/
  main.py               — pipeline orchestration
  serpapi_client.py     — SerpApi Google News fetcher
  company_matcher.py    — fuzzy company name matching (returns name + priority)
  news_scorer.py        — scoring with Indian DC / India / global priority tiers
  dedupe.py             — multi-layer dedup (URL + fuzzy title + key term extraction)
  digest_builder.py     — per-article summaries + formatted summary digest
  image_gen.py          — article image cards (OG image fetch + Pillow fallback with Express logo)
  storage.py            — CSV/JSON persistence + sent tracking
  whatsapp_sender.py    — spawns Node.js sender (single + multi-message batch)
  config.py             — env-based configuration
data/
  queries.csv           — 10 targeted search queries
  companies.csv         — 40 Indian data centre companies
  news_log.csv          — article storage + sent status
send_to_community.js    — WhatsApp Web sender (handles image + text messages)
run_daily.py            — entry point
startup.bat             — one-click setup + run
express_logo.png        — logo placed on generated image cards
```

## Pipeline flow

```
fetch(248) → 24h filter → dedup → score with priority boost
  → top 15 by score → 15 individual image+summary messages
  → 1 formatted summary digest
```

## Priority scoring

| Tier | Examples | Boost |
|------|----------|-------|
| Indian DC companies | CtrlS, Sify, Pi Datacentres, Bharti Airtel, TATA, NTT, STT GDC, Yotta, AdaniConneX | +60 |
| International with India presence | AWS India, Google Cloud India, Microsoft India, Equinix India | +40 |
| India mentions | Hyderabad, Mumbai, Bengaluru, "India" in text | +10–15 |
| Rest | Global news | base score only |

## Config

| Env var | Default | Description |
|---------|---------|-------------|
| `MIN_SCORE` | 20 | Minimum relevance score |
| `MAX_ARTICLES` | 15 | Top N articles to send |
| `MAX_SEND_MESSAGES` | 0 | 0 = send all, >0 limits for testing |

## Notes

- Group send uses `WAWebSendMsgChatAction.addAndSendMsgToChat()` for text and `client.sendMessage()` with `MessageMedia` for images.
- Retries 3 times with Chrome restart between attempts.
- Image temp files cleaned up after sending.
