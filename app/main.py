from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Request, Response

from app.bot import create_dispatcher, set_db_pool
from app.config import config
from app.db import create_pool, init_db, postgres_enabled

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

dp = create_dispatcher()
bot: Bot | None = None
db_pool = None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    global bot
    global db_pool
    if config.TELEGRAM_BOT_TOKEN:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        if config.WEBHOOK_URL:
            try:
                await bot.set_webhook(config.WEBHOOK_URL + "/tg/webhook")
                logger.info("Webhook set to %s/tg/webhook", config.WEBHOOK_URL)
            except Exception as exc:
                logger.exception("Failed to set webhook: %s", exc)
        else:
            logger.warning("WEBHOOK_URL is not set; webhook not registered")
    else:
        logger.error("TELEGRAM_BOT_TOKEN is not set")

    if postgres_enabled():
        try:
            db_pool = await create_pool()
            await init_db(db_pool)
            set_db_pool(db_pool)
            logger.info("PostgreSQL pool initialized")
        except Exception as exc:
            logger.exception("Failed to initialize PostgreSQL pool: %s", exc)
    else:
        logger.warning("PostgreSQL is not configured; request logging disabled")

    yield

    set_db_pool(None)
    if db_pool is not None:
        await db_pool.close()
    if bot:
        await bot.session.close()


app = FastAPI(title="ATG INN Check Bot", lifespan=lifespan)


@app.post("/tg/webhook")
async def telegram_webhook(request: Request) -> Response:
    if bot is None:
        return Response(status_code=503)
    body = await request.json()
    update = Update.model_validate(body)
    logger.info("Update received: %s", update.update_id)
    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=200)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
