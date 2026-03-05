from __future__ import annotations

import os


class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    DADATA_API_KEY: str = os.getenv("DADATA_API_KEY", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")


config = Config()
