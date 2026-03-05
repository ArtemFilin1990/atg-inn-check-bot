from __future__ import annotations

import logging
from json import JSONDecodeError
from contextlib import asynccontextmanager
from typing import AsyncIterator

from aiogram import Bot
from pydantic import ValidationError
from aiogram.types import Update
from fastapi import FastAPI, Request, Response

from app.bot import create_dispatcher
from app.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

dp = create_dispatcher()
bot: Bot | None = None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    global bot
    if config.TELEGRAM_BOT_TOKEN:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        if config.WEBHOOK_URL:
            try:
                webhook_base = config.WEBHOOK_URL.rstrip("/")
                await bot.set_webhook(webhook_base + "/tg/webhook")
                logger.info("Webhook set to %s/tg/webhook", webhook_base)
            except Exception as exc:
                logger.exception("Failed to set webhook: %s", exc)
        else:
            logger.warning("WEBHOOK_URL is not set; webhook not registered")
    else:
        logger.error("TELEGRAM_BOT_TOKEN is not set")

    yield

    if bot:
        await bot.session.close()
        bot = None


app = FastAPI(title="ATG INN Check Bot", lifespan=lifespan)


@app.post("/tg/webhook")
async def telegram_webhook(request: Request) -> Response:
    if bot is None:
        return Response(status_code=503)

    try:
        body = await request.json()
    except (JSONDecodeError, ValueError):
        logger.warning("Invalid JSON payload for /tg/webhook")
        return Response(status_code=400)

    try:
        update = Update.model_validate(body)
    except ValidationError:
        logger.warning("Invalid Telegram update payload for /tg/webhook")
        return Response(status_code=400)

    logger.info("Update received: %s", update.update_id)
    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=200)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
