import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from aiogram import Bot
from aiogram.types import Update

from app.dadata_client import DaDataClient
from app.rate_limit import RateLimiter
from app.bot import create_dispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
DADATA_API_KEY: str = os.environ["DADATA_API_KEY"]
WEBHOOK_URL: str = os.environ["WEBHOOK_URL"]  # e.g. https://myapp.amvera.io
PORT: int = int(os.environ.get("PORT", "8000"))
WEBHOOK_PATH: str = "/tg/webhook"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dadata = DaDataClient(api_key=DADATA_API_KEY)
limiter = RateLimiter(rate=25)
dp = create_dispatcher(dadata, limiter)


@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_full = WEBHOOK_URL.rstrip("/") + WEBHOOK_PATH
    await bot.set_webhook(webhook_full)
    logger.info("Webhook set to %s", webhook_full)
    yield
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Webhook deleted, bot session closed")


app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> Response:
    body = await request.json()
    update = Update.model_validate(body)
    await dp.feed_update(bot, update)
    return Response(status_code=200)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
