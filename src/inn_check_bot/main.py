import os
import logging
import re
from typing import Optional, Dict
import requests
from cachetools import TTLCache
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=1000, ttl=int(os.environ.get('CACHE_TTL', '600')))

feedback_stats: Dict[str, int] = {'helpful': 0, 'not_helpful': 0}

FEEDBACK_WAITING: Dict[int, bool] = {}

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
    management = data.get('management')
    if management:
        ceo_name = management.get('name')
        ceo_post = management.get('post')
        if ceo_name:
            message += f"\nРуководитель: {f'{ceo_post} ' if ceo_post else ''}{ceo_name}"
    okved = data.get('okved')
    if okved:
        message += f"\nОКВЭД: {okved}"
    risk_flags = []
    if status == 'LIQUIDATED':
        risk_flags.append('⛔ Организация ликвидирована')
    elif status == 'BANKRUPT':
        risk_flags.append('⛔ Организация признана банкротом')
    elif status == 'LIQUIDATING':
        risk_flags.append('⚠️ Организация в процессе ликвидации')
    elif status == 'REORGANIZING':
        risk_flags.append('⚠️ Организация в процессе реорганизации')
    if risk_flags:
        message += '\n\nРиски:\n' + '\n'.join(risk_flags)
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [['🏕️ Старт', '👋 Привет'], ['🔎 Проверить ИНН']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        'Добро пожаловать! Я могу проверить ИНН организации или ИП.\n'
        'Нажмите кнопку или отправьте ИНН (10 или 12 цифр).',
        reply_markup=reply_markup
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if text == '🏕️ Старт':
        await start(update, context)
        return
    if text == '👋 Привет':
        await update.message.reply_text('Привет! Отправьте ИНН для проверки.')
        return
    if text == '🔎 Проверить ИНН':
        await update.message.reply_text('Пожалуйста, отправьте ИНН (10 или 12 цифр).')
        return
    user_id = update.effective_user.id
    if FEEDBACK_WAITING.pop(user_id, False):
        logger.info("User feedback from %s: %s", user_id, text)
        await update.message.reply_text('Спасибо за ваш отзыв! Мы постараемся улучшить бота.')
        return
    inn = validate_inn(text)
    if not inn:
        await update.message.reply_text('Введите корректный ИНН (10 или 12 цифр).')
        return
    await update.message.reply_text('Ищу информацию, пожалуйста, подождите...')
    info = fetch_dadata(inn)
    if info:
        message = format_info(info)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton('👍 Полезно', callback_data=f'feedback:helpful:{inn}'),
                InlineKeyboardButton('👎 Не полезно', callback_data=f'feedback:not_helpful:{inn}'),
            ]
        ])
        await update.message.reply_text(message, reply_markup=keyboard)
    else:
        await update.message.reply_text('Не удалось получить информацию. Попробуйте позже.')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Отправьте ИНН (10 или 12 цифр), чтобы получить сведения о компании или ИП.\n'
        'Команда /feedback — отправить предложение по улучшению бота.'
    )

async def feedback_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = ' '.join(context.args) if context.args else ''
    if text:
        logger.info("User feedback from %s: %s", update.effective_user.id, text)
        await update.message.reply_text('Спасибо за ваш отзыв! Мы постараемся улучшить бота.')
    else:
        FEEDBACK_WAITING[update.effective_user.id] = True
        await update.message.reply_text('Пожалуйста, напишите ваше предложение или замечание по работе бота.')

async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(':', 2)
    if len(parts) < 2:
        return
    rating = parts[1]
    if rating not in ('helpful', 'not_helpful'):
        return
    inn = parts[2] if len(parts) > 2 else 'unknown'
    feedback_stats[rating] += 1
    logger.info(
        "Feedback '%s' for INN %s from user %s (helpful=%d, not_helpful=%d)",
        rating, inn, query.from_user.id,
        feedback_stats.get('helpful', 0), feedback_stats.get('not_helpful', 0),
    )
    if rating == 'helpful':
        reply = '👍 Спасибо! Рады, что информация оказалась полезной.'
    else:
        reply = '👎 Спасибо за отзыв! Отправьте /feedback с описанием проблемы, чтобы помочь нам улучшить бота.'
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(reply)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def build_application() -> Application:
    token = os.environ.get('BOT_TOKEN')
    if not token:
        raise RuntimeError('BOT_TOKEN is not set')
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('feedback', feedback_cmd))
    app.add_handler(CallbackQueryHandler(feedback_callback, pattern=r'^feedback:'))
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
