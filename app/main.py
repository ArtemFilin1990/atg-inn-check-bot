from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Request, Response

from app.bot import create_dispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL: str = os.environ.get("WEBHOOK_URL", "")

dp = create_dispatcher()
bot: Bot | None = None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    global bot
    if TOKEN:
        bot = Bot(token=TOKEN)
        if WEBHOOK_URL:
            try:
                await bot.set_webhook(WEBHOOK_URL + "/tg/webhook")
                logger.info("Webhook set to %s/tg/webhook", WEBHOOK_URL)
            except Exception as exc:
                logger.exception("Failed to set webhook: %s", exc)
        else:
            logger.warning("WEBHOOK_URL is not set; webhook not registered")
    else:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
    yield
    if bot:
        await bot.session.close()


app = FastAPI(title="ATG INN Check Bot", lifespan=lifespan)


@app.post("/tg/webhook")
async def telegram_webhook(request: Request) -> Response:
    if bot is None:
        return Response(status_code=503)
    body = await request.json()
    update = Update.model_validate(body)
    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=200)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
