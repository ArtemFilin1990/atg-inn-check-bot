from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.bot import create_dispatcher, set_db_pool
from app.config import config
from app.db import create_pool, init_db, postgres_enabled

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/tg/webhook"


def _ensure_project_root_on_syspath(project_file: str) -> None:
    project_root = str(Path(project_file).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def _build_webhook_url(base_url: str) -> str | None:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        return None

    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("WEBHOOK_URL must be a valid absolute http(s) URL")
    return f"{cleaned}{WEBHOOK_PATH}"


_ensure_project_root_on_syspath(__file__)

dp = create_dispatcher()
bot: Bot | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global bot

    db_pool = None
    if postgres_enabled():
        try:
            db_pool = await create_pool()
            await init_db(db_pool)
            set_db_pool(db_pool)
            logger.info("PostgreSQL logging enabled")
        except Exception:
            logger.exception("Failed to initialize PostgreSQL; continuing without DB logging")
            set_db_pool(None)
            db_pool = None

    local_bot: Bot | None = None
    token = (config.TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set, webhook endpoint will return 503")
    else:
        local_bot = Bot(token=token)
        bot = local_bot
        try:
            webhook_url = _build_webhook_url(config.WEBHOOK_URL)
            if webhook_url is None:
                logger.info("WEBHOOK_URL is empty, skipping Telegram setWebhook (local smoke mode)")
            else:
                await local_bot.set_webhook(webhook_url)
                logger.info("Telegram webhook configured: %s", webhook_url)
        except ValueError as exc:
            logger.warning("Invalid WEBHOOK_URL, skipping Telegram setWebhook: %s", exc)
        except Exception:
            logger.exception("Failed to register Telegram webhook")

    try:
        yield
    finally:
        if local_bot is not None:
            await local_bot.session.close()
        if db_pool is not None:
            await db_pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> JSONResponse:
    if bot is None:
        raise HTTPException(status_code=503, detail="Bot is not configured")

    try:
        payload: dict[str, Any] = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    try:
        update = Update.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram update payload") from exc

    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})
