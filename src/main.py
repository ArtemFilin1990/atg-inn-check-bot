import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot import handlers, callbacks
from clients.dadata import DadataClient
from clients.nalog import NalogClient
from services.aggregator import Aggregator
from services.cache import SQLiteCache
from services.reference_data import ReferenceData
from storage.session_store import SessionStore
from http_api import health_handler, create_lookup_handler, rate_limiter_from_env

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=os.environ.get('LOG_LEVEL', 'INFO'),
)
logger = logging.getLogger(__name__)


class ServiceMiddleware:
    """Inject aggregator and sessions into handler context."""

    def __init__(self, aggregator: Aggregator, sessions: SessionStore):
        self.aggregator = aggregator
        self.sessions = sessions

    async def __call__(self, handler, event, data):
        data['aggregator'] = self.aggregator
        data['sessions'] = self.sessions
        return await handler(event, data)


async def main():
    token = os.environ['BOT_TOKEN']
    dadata_token = os.environ.get('DADATA_API_KEY') or os.environ.get('DADATA_TOKEN', '')
    dadata_secret = os.environ.get('DADATA_SECRET', '')
    if not dadata_token:
        logger.warning("DADATA_API_KEY/DADATA_TOKEN is not set; DaData requests will fail")

    # Initialise services
    cache = SQLiteCache()
    await cache.init()

    ref_data = ReferenceData()
    await ref_data.init()

    sessions = SessionStore()
    await sessions.init()

    dadata = DadataClient(token=dadata_token, secret=dadata_secret)
    nalog = NalogClient(timeout=int(os.environ.get('HTTP_TIMEOUT_SECONDS', '5')))

    aggregator = Aggregator(
        dadata=dadata,
        cache=cache,
        ref_data=ref_data,
        nalog=nalog,
    )

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    await bot.set_my_commands([
        BotCommand(command='start', description='Начать работу с ботом'),
        BotCommand(command='help', description='Помощь и список режимов'),
        BotCommand(command='feedback', description='Отправить предложение или замечание'),
    ])

    # Register middleware
    middleware = ServiceMiddleware(aggregator=aggregator, sessions=sessions)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    dp.include_router(handlers.router)
    dp.include_router(callbacks.router)

    webhook_base = os.environ.get('WEBHOOK_BASE', '').rstrip('/')
    mode = 'webhook' if webhook_base else os.environ.get('MODE', 'polling')
    try:
        if mode == 'webhook':
            from aiohttp import web
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            webhook_path = os.environ.get('WEBHOOK_PATH', '/webhook')
            webhook_url = webhook_base or os.environ['WEBHOOK_URL']
            port = int(os.environ.get('PORT', '3000'))
            await bot.set_webhook(f'{webhook_url}{webhook_path}')
            app = web.Application()
            SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
            setup_application(app, dp, bot=bot)
            app.router.add_get('/health', health_handler)
            app.router.add_post('/lookup', create_lookup_handler(aggregator, rate_limiter_from_env()))
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            logger.info("Webhook started on port %d", port)
            await asyncio.Event().wait()
        else:
            logger.info("Starting polling")
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await dadata.close()
        await nalog.close()
        await cache.close()
        await ref_data.close()
        await sessions.close()
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
