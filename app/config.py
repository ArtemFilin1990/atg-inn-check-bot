from __future__ import annotations

import os


class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    DADATA_API_KEY: str = os.getenv("DADATA_API_KEY", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

    # PostgreSQL
    POSTGRES_HOST: str | None = os.getenv("POSTGRES_HOST")
    _postgres_port_raw: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_PORT: int = int(_postgres_port_raw) if _postgres_port_raw.isdigit() else 5432
    POSTGRES_DB: str | None = os.getenv("POSTGRES_DB")
    POSTGRES_USER: str | None = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str | None = os.getenv("POSTGRES_PASSWORD")


config = Config()
