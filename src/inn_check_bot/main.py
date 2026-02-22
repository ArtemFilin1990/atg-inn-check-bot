import os
import logging
import re
from typing import Optional, Dict
import requests
from cachetools import TTLCache
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=1000, ttl=int(os.environ.get('CACHE_TTL', '600')))

def validate_inn(text: str) -> Optional[str]:
    inn = re.sub(r'\D', '', text)
    if inn.isdigit() and len(inn) in (10, 12):
        return inn
    return None

def fetch_dadata(inn: str) -> Optional[Dict]:
    if inn in cache:
        return cache[inn]
    token = os.environ.get('DADATA_TOKEN')
    secret = os.environ.get('DADATA_SECRET')
    if not token or not secret:
        logger.error("DADATA_TOKEN or DADATA_SECRET is not set")
        return None
    url = 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party'
    headers = {
        'Authorization': f'Token {token}',
        'X-Secret': secret,
        'Content-Type': 'application/json'
    }
    payload = {'query': inn, 'branch_type': 'MAIN'}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        suggestions = data.get('suggestions')
        if suggestions:
            result = suggestions[0]
            cache[inn] = result
            return result
    except Exception as e:
        logger.exception("Error fetching data from DaData: %s", e)
    return None

def format_info(info: Dict) -> str:
    data = info.get('data', {})
    name = data.get('name', {}).get('short_with_opf') or data.get('name', {}).get('full_with_opf')
    ogrn = data.get('ogrn')
    inn = data.get('inn')
    kpp = data.get('kpp')
    address = data.get('address', {}).get('unrestricted_value')
    state = data.get('state', {})
    status = state.get('status')
    status_name = state.get('name')
    message = f"Название: {name}\nИНН/КПП: {inn}/{kpp}\nОГРН: {ogrn}\nАдрес: {address}\nСтатус: {status_name} ({status})"
    okved = data.get('okved')
    if okved:
        message += f"\nОКВЭД: {okved}"
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [['👋 Привет', '🔍 Проверить ИНН']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        'Добро пожаловать! Я могу проверить ИНН организации или ИП.\n'
        'Нажмите кнопку или отправьте ИНН (10 или 12 цифр).',
        reply_markup=reply_markup
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if text == '👋 Привет':
        await update.message.reply_text('Привет! Отправьте ИНН для проверки.')
        return
    if text == '🔍 Проверить ИНН':
        await update.message.reply_text('Пожалуйста, отправьте ИНН (10 или 12 цифр).')
        return
    inn = validate_inn(text)
    if not inn:
        await update.message.reply_text('Введите корректный ИНН (10 или 12 цифр).')
        return
    await update.message.reply_text('Ищу информацию, пожалуйста, подождите...')
    info = fetch_dadata(inn)
    if info:
        message = format_info(info)
        await update.message.reply_text(message)
    else:
        await update.message.reply_text('Не удалось получить информацию. Попробуйте позже.')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Отправьте ИНН (10 или 12 цифр), чтобы получить сведения о компании или ИП.')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def build_application() -> Application:
    token = os.environ.get('BOT_TOKEN')
    if not token:
        raise RuntimeError('BOT_TOKEN is not set')
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)
    return app

def run() -> None:
    application = build_application()
    mode = os.environ.get('MODE', 'polling')
    if mode == 'webhook':
        host = '0.0.0.0'
        port = int(os.environ.get('PORT', '3000'))
        webhook_path = os.environ.get('WEBHOOK_PATH', '')
        webhook_url = os.environ.get('WEBHOOK_URL', '')
        if not webhook_url:
            raise RuntimeError('WEBHOOK_URL must be set in webhook mode')
        application.run_webhook(
            listen=host,
            port=port,
            url_path=webhook_path,
            webhook_url=f"{webhook_url}{webhook_path}"
        )
    else:
        application.run_polling()

if __name__ == '__main__':
    run()
