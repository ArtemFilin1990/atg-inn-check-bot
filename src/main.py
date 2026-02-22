import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot import handlers, callbacks
from clients.checko import CheckoClient
from clients.dadata import DadataClient
from services.aggregator import Aggregator
from services.cache import SQLiteCache
from services.reference_data import ReferenceData
from storage.session_store import SessionStore

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
    checko_key = os.environ.get('CHECKO_API_KEY', '')
    if not checko_key:
        logger.warning("CHECKO_API_KEY is not set; Checko requests will fail")
    dadata_token = os.environ.get('DADATA_API_KEY') or os.environ.get('DADATA_TOKEN', '')
    dadata_secret = os.environ.get('DADATA_SECRET', '')

    # Initialise services
    cache = SQLiteCache()
    await cache.init()

    ref_data = ReferenceData()
    await ref_data.init()

    sessions = SessionStore()
    await sessions.init()

    checko = CheckoClient(api_key=checko_key)
    dadata = DadataClient(token=dadata_token, secret=dadata_secret)

    aggregator = Aggregator(
        checko=checko,
        dadata=dadata,
        cache=cache,
        ref_data=ref_data,
    )

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register middleware
    middleware = ServiceMiddleware(aggregator=aggregator, sessions=sessions)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    dp.include_router(handlers.router)
    dp.include_router(callbacks.router)

    mode = os.environ.get('MODE', 'polling')
    try:
        if mode == 'webhook':
            from aiohttp import web
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            webhook_url = os.environ['WEBHOOK_URL']
            webhook_path = os.environ.get('WEBHOOK_PATH', '/webhook')
            port = int(os.environ.get('PORT', '80'))
            await bot.set_webhook(f'{webhook_url}{webhook_path}')
            app = web.Application()
            SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
            setup_application(app, dp, bot=bot)
            # health endpoint
            async def health(_):
                return web.Response(text='ok')
            app.router.add_get('/health', health)
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
        await checko.close()
        await dadata.close()
        await cache.close()
        await ref_data.close()
        await sessions.close()
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
