# tg-inn-check-bot

This repository contains a Telegram bot for checking Russian organizations or sole proprietors by INN (tax ID) using the DaData “findById/party” API on the “Max” tariff.

## Features

- Reply keyboard with 3 modes: 🏢 ООО, 👤 ИП, 🧍 Физлицо.
- For ООО uses `findById/party` with `type=LEGAL` and INN(10)/OGRN(13).
- For ИП uses `findById/party` with `type=INDIVIDUAL` and INN(12)/OGRNIP(15).
- For Физлицо uses `suggest/party` by full name, then loads full card via `findById/party`.
- Validates inputs by selected mode and returns summary + full JSON in chunks.
- Displays company name, INN/OGRN/KPP, status, address, CEO, and OKVED.
- Shows simple risk flags based only on DaData fields (e.g. liquidation status).
- Supports both polling and webhook modes (configurable via env vars).
- HTTP API in webhook mode: `GET /health` and `POST /lookup` (port 3000 by default).
- Caching of results to reduce API calls (TTL 10–30 minutes).
- **Continuous improvement skill**: after each INN lookup users can rate the result with 👍/👎 inline buttons; freeform feedback can be submitted via `/feedback`.

## Getting started

1. Clone this repository.
2. Install Python 3.11+ and create a virtual environment.
3. Install dependencies from `requirements.txt`:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in your tokens:

   - `BOT_TOKEN` – Telegram bot token.
   - `DADATA_TOKEN` (or `DADATA_API_KEY`) – DaData API token.
   - `DADATA_SECRET` – DaData secret (optional).
   - `WEBHOOK_BASE` (optional) – if set, bot runs webhook mode at `<WEBHOOK_BASE>/webhook`.
   - `MODE` – `polling` or `webhook` (used when `WEBHOOK_BASE` is not set).
   - `WEBHOOK_URL` and `WEBHOOK_PATH` – fallback webhook vars for compatibility. In webhook mode, at least one of `WEBHOOK_BASE` or `WEBHOOK_URL` must be set.
   - `PORT` – port for webhook and HTTP API (default 3000).
   - `LOOKUP_RATE_LIMIT_RPS` – rate limit for `/lookup` per client IP (default `1`).

5. Run the bot in polling mode:

   ```bash
   MODE=polling python src/main.py
   ```

   Or in webhook mode:

   ```bash
   WEBHOOK_BASE=<your public url> PORT=3000 python src/main.py
   ```

6. Deploy to Amvera by building the `Dockerfile` and setting environment variables accordingly.


### HTTP API (webhook mode)

When running in webhook mode (`WEBHOOK_BASE` or `MODE=webhook`), the service also exposes:

- `GET /health` → `{"status": "ok"}`
- `POST /lookup` → lookup by INN/OGRN via existing aggregator/cache

`POST /lookup` body:

```json
{
  "query": "7736207543",
  "entity_type": "LEGAL",
  "count": 10
}
```

Fields:
- `query` (required): INN/OGRN/OGRNIP string.
- `entity_type` (optional): `LEGAL` or `INDIVIDUAL`.
- `count` (optional): integer from 1 to 20.

## Project structure

```
src/
├─ bot/                   # aiogram handlers, callbacks, keyboards
├─ clients/               # external API clients (DaData)
├─ services/              # aggregation, cache, reference data
└─ main.py                # entry point
Dockerfile
amvera.yml
requirements.txt
.env.example
README.md
```


### Use Codex in GitHub review flow

- In a PR comment, write `@codex review` to request a review.
- Optionally add focus, e.g. `@codex review for security regressions`.
- Codex review behavior can be tuned with repository `AGENTS.md` review guidelines.
