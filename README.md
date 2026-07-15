# IndianWhatsappAutomation

Daily Indian data centre news scraper + WhatsApp digest delivery.

## How it works

1. **Scrape** — Fetches news from SerpApi Google News engine using 10 targeted queries for data centre land/project announcements in India.
2. **Score** — Matches articles against 40 Indian data centre companies, scores by relevance (land, project, high-value keywords), filters to today's date.
3. **Deduplicate** — Removes duplicates across queries and previous runs by link + fuzzy title match.
4. **Digest** — Builds a formatted digest grouped by Land Acquisition and New Projects/Expansions.
5. **Send** — Delivers to a WhatsApp Community group via `whatsapp-web.js` using the low-level `WAWebSendMsgChatAction.addAndSendMsgToChat()` API (bypasses a library bug where `Msg.get()` returns null for group sends).

## Setup

```bash
git clone https://github.com/ExpressRupya/IndianWhatsappAutomation.git
cd IndianWhatsappAutomation
```

### Environment (`.env`)

```
SERPAPI_KEY=your_serpapi_key
MIN_SCORE=20
MAX_DIGEST_ITEMS=10
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
venv\Scripts\python run_daily.py
```

First run requires WhatsApp QR authentication via `setup_whatsapp.js`.

## Project structure

```
app/
  main.py               — pipeline orchestration
  serpapi_client.py     — SerpApi Google News fetcher
  company_matcher.py    — fuzzy company name matching
  news_scorer.py        — article scoring by land/project keywords
  dedupe.py             — link + fuzzy title dedup
  digest_builder.py     — formats the WhatsApp message
  storage.py            — CSV/JSON persistence + sent tracking
  whatsapp_sender.py    — spawns Node.js sender with retries
  config.py             — env-based configuration
data/
  queries.csv           — 10 targeted search queries
  companies.csv         — 40 Indian data centre companies
  news_log.csv          — article storage + sent status
send_to_community.js    — WhatsApp Web sender (low-level API)
run_daily.py            — entry point
startup.bat             — one-click setup + run
```

## Queries

Targets land acquisition, project announcements, and expansions for key Indian data centre operators: CtrlS, Nxtra, Yotta, Equinix, NTT, AdaniConneX, STT GDC, Sify, TATA Communications, Reliance/Jio, Microsoft, AWS, Google Cloud, and more.

## Notes

- Group send uses `WAWebSendMsgChatAction.addAndSendMsgToChat()` directly because `whatsapp-web.js`'s `client.sendMessage()` returns `undefined` for `@g.us` chats (the `Msg.get()` call after `addAndSendMsgToChat` returns null, but the message IS sent).
- Retries 3 times with Chrome restart between attempts.
- SerialpAPI `when:1d` parameter is appended to all queries.
