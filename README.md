# tg-inn-check-bot

This repository contains a Telegram bot for checking Russian organizations or sole proprietors by INN (tax ID) using the DaData “findById/party” API on the “Max” tariff.

## Features

- Reply keyboard with quick commands: 🏕️ Старт, 👋 Привет, 🔎 Проверить ИНН.
- Validates that the input consists of 10 or 12 digits.
- Requests DaData for full company information.
- Displays company name, INN/OGRN/KPP, status, address, CEO, and OKVED.
- Shows simple risk flags based only on DaData fields (e.g. liquidation status).
- Supports both polling and webhook modes (configurable via env vars).
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
   - `DADATA_API_KEY` (or `DADATA_TOKEN`) – DaData API token.
   - `DADATA_SECRET` – DaData secret (optional).
   - `MODE` – `polling` or `webhook`.
   - `WEBHOOK_URL` and `WEBHOOK_PATH` – for webhook mode.
   - `PORT` – port for webhook (default 3000).

5. Run the bot in polling mode:

   ```bash
   MODE=polling PYTHONPATH=src python -m main
   ```

   Or in webhook mode:

   ```bash
   MODE=webhook WEBHOOK_URL=<your public url> WEBHOOK_PATH=<secret path> PYTHONPATH=src python -m main
   ```

6. Deploy to Amvera by building the `Dockerfile` and setting environment variables accordingly.

## Project structure

```
src/inn_check_bot/        # Python package
├─┐ __init__.py
├─┐ __main__.py
└─┐ main.py               # entry point
Dockerfile
requirements.txt
.env.example
README.md
```
