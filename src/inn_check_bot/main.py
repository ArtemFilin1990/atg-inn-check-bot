import os
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict
import httpx
from dadata import DadataAsync
from cachetools import TTLCache
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=1000, ttl=int(os.environ.get('CACHE_TTL', '600')))

_RE_NON_DIGITS = re.compile(r'\D')

feedback_stats: Dict[str, int] = {'helpful': 0, 'not_helpful': 0}

# Conversation state
AWAITING_INN = 0

# User-data key that stores which scenario is active
MODE_KEY = 'inn_mode'
MODE_ORG = 'org'
MODE_IP = 'ip'
MODE_INDIV = 'indiv'
MODE_UNIVERSAL = 'universal'

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [['🏢 Всё об организации', '👤 Всё об ИП'], ['🧑 Физлицо', '🔎 Проверить ИНН']],
    resize_keyboard=True,
)

# Button labels used to detect mode switches inside the conversation
_MODE_BUTTONS = {'🏢 Всё об организации', '👤 Всё об ИП', '🧑 Физлицо', '🔎 Проверить ИНН'}


def validate_inn(text: str) -> Optional[str]:
    inn = _RE_NON_DIGITS.sub('', text)
    if inn.isdigit() and len(inn) in (10, 12):
        return inn
    return None


async def fetch_dadata(inn: str, client: DadataAsync) -> Optional[Dict]:
    if inn in cache:
        logger.debug("Cache hit for INN %s", inn)
        return cache[inn]
    token = os.environ.get('DADATA_TOKEN')
    secret = os.environ.get('DADATA_SECRET')
    if not token or not secret:
        logger.error("DADATA_TOKEN or DADATA_SECRET is not set")
        return None
    try:
        suggestions = await client.find_by_id(name="party", query=inn, branch_type="MAIN")
        if suggestions:
            result = suggestions[0]
            cache[inn] = result
            return result
        logger.info("DaData returned no suggestions for INN %s", inn)
    except Exception as e:
        logger.exception("Error fetching data from DaData: %s", e)
    return None


def _format_date(ts_ms: Optional[int]) -> str:
    if ts_ms is None:
        return 'неизвестно'
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%d.%m.%Y')
    except Exception:
        return 'неизвестно'


def format_org_info(info: Dict) -> str:
    data = info.get('data', {}) or {}
    name = (
        data.get('name', {}).get('full_with_opf')
        or data.get('name', {}).get('short_with_opf')
        or '—'
    )
    ogrn = data.get('ogrn') or '—'
    inn = data.get('inn') or '—'
    kpp = data.get('kpp') or '—'
    address = (data.get('address') or {}).get('unrestricted_value') or '—'
    state = data.get('state') or {}
    status = state.get('status')
    status_name = state.get('name') or status or '—'
    reg_date = _format_date(state.get('registration_date'))

    lines = [
        '🏢 Организация',
        f'Полное наименование: {name}',
        f'ИНН/КПП: {inn}/{kpp}',
        f'ОГРН: {ogrn}',
        f'Статус: {status_name}',
        f'Дата регистрации: {reg_date}',
        f'Адрес: {address}',
    ]

    management = data.get('management')
    if management:
        ceo_name = management.get('name')
        ceo_post = management.get('post')
        if ceo_name:
            lines.append(f'Руководитель: {f"{ceo_post} " if ceo_post else ""}{ceo_name}')

    okved = data.get('okved')
    if okved:
        lines.append(f'ОКВЭД: {okved}')

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
        lines.append('\nПризнаки риска:\n' + '\n'.join(risk_flags))

    return '\n'.join(lines)


def format_ip_info(info: Dict) -> str:
    data = info.get('data', {}) or {}
    # Name precedence: top-level `value` (full display name) > data.name.full > fallback
    name = info.get('value') or (data.get('name') or {}).get('full') or '—'
    ogrn = data.get('ogrn') or '—'
    inn = data.get('inn') or '—'
    state = data.get('state') or {}
    status = state.get('status')
    status_name = state.get('name') or status or '—'
    reg_date = _format_date(state.get('registration_date'))
    address = (data.get('address') or {}).get('unrestricted_value') or '—'
    okved = data.get('okved') or '—'

    lines = [
        '👤 ИП',
        f'ФИО: {name}',
        f'ИНН: {inn}',
        f'ОГРНИП: {ogrn}',
        f'Статус: {status_name}',
        f'Дата регистрации: {reg_date}',
        f'Регион: {address}',
        f'ОКВЭД: {okved}',
    ]

    risk_flags = []
    if status == 'LIQUIDATED':
        risk_flags.append('⛔ ИП прекратил деятельность')
    elif status == 'LIQUIDATING':
        risk_flags.append('⚠️ ИП в процессе ликвидации')

    if risk_flags:
        lines.append('\nПризнаки риска:\n' + '\n'.join(risk_flags))

    return '\n'.join(lines)


def format_individual_info(info: Dict) -> str:
    """Return only legally available data for an individual."""
    data = info.get('data', {}) or {}
    inn = data.get('inn') or '—'
    state = data.get('state') or {}
    status_name = state.get('name') or state.get('status') or '—'
    address = (data.get('address') or {}).get('unrestricted_value') or '—'

    lines = [
        '🧑 Физлицо',
        f'ИНН: {inn}',
        f'Статус в налоговой: {status_name}',
        f'Регион регистрации: {address}',
    ]
    return '\n'.join(lines)


# Keep for backwards compatibility
def format_info(info: Dict) -> str:
    return format_org_info(info)


n


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s issued /start", update.effective_user.id)
    await update.message.reply_text(
        'Добро пожаловать! Я могу проверить ИНН организации, ИП или физлица.\n'
        'Выберите режим проверки:',
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("User %s issued /help", update.effective_user.id)
    await update.message.reply_text(
        'Выберите кнопку для проверки ИНН:\n'
        '🏢 Всё об организации — ИНН из 10 цифр\n'
        '👤 Всё об ИП — ИНН из 12 цифр\n'
        '🧑 Физлицо — ИНН из 12 цифр\n'
        '🔎 Проверить ИНН — универсальный режим (10 или 12 цифр)\n\n'
        'Команда /feedback — отправить предложение по улучшению бота.',
        reply_markup=MAIN_KEYBOARD,
    )


async def feedback_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = ' '.join(context.args) if context.args else ''
    if text:
        logger.info("User feedback from %s: %s", update.effective_user.id, text)
        await update.message.reply_text('Спасибо за ваш отзыв! Мы постараемся улучшить бота.')
    else:
        await update.message.reply_text(
            'Пожалуйста, напишите ваше предложение или замечание после команды:\n'
            '/feedback <ваш текст>'
        )


# ── entry-point handlers (set mode and ask for INN) ──────────────────────────

async def ask_org_inn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[MODE_KEY] = MODE_ORG
    logger.info("User %s selected mode %s", update.effective_user.id, MODE_ORG)
    await update.message.reply_text('Введите ИНН организации (10 цифр).')
    return AWAITING_INN


async def ask_ip_inn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[MODE_KEY] = MODE_IP
    logger.info("User %s selected mode %s", update.effective_user.id, MODE_IP)
    await update.message.reply_text('Введите ИНН ИП (12 цифр).')
    return AWAITING_INN


async def ask_indiv_inn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[MODE_KEY] = MODE_INDIV
    logger.info("User %s selected mode %s", update.effective_user.id, MODE_INDIV)
    await update.message.reply_text('Введите ИНН физлица (12 цифр).')
    return AWAITING_INN


async def ask_universal_inn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[MODE_KEY] = MODE_UNIVERSAL
    logger.info("User %s selected mode %s", update.effective_user.id, MODE_UNIVERSAL)
    await update.message.reply_text('Введите ИНН (10 или 12 цифр).')
    return AWAITING_INN


# ── state handler ─────────────────────────────────────────────────────────────

async def handle_inn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the INN text received while in AWAITING_INN state."""
    text = update.message.text.strip()

    # Allow switching mode by pressing a different keyboard button
    if text == '🏢 Всё об организации':
        return await ask_org_inn(update, context)
    if text == '👤 Всё об ИП':
        return await ask_ip_inn(update, context)
    if text == '🧑 Физлицо':
        return await ask_indiv_inn(update, context)
    if text == '🔎 Проверить ИНН':
        return await ask_universal_inn(update, context)

    mode = context.user_data.get(MODE_KEY, MODE_UNIVERSAL)
    inn_raw = _RE_NON_DIGITS.sub('', text)
    user_id = update.effective_user.id

    # Validate length based on mode
    if mode == MODE_ORG:
        if not inn_raw.isdigit() or len(inn_raw) != 10:
            logger.warning("User %s submitted invalid INN %r (mode=%s)", user_id, inn_raw, mode)
            await update.message.reply_text('ИНН должен содержать 10 цифр без пробелов.')
            return AWAITING_INN
    elif mode in (MODE_IP, MODE_INDIV):
        if not inn_raw.isdigit() or len(inn_raw) != 12:
            logger.warning("User %s submitted invalid INN %r (mode=%s)", user_id, inn_raw, mode)
            await update.message.reply_text('ИНН должен содержать 12 цифр без пробелов.')
            return AWAITING_INN
    else:  # universal
        if not inn_raw.isdigit() or len(inn_raw) not in (10, 12):
            logger.warning("User %s submitted invalid INN %r (mode=%s)", user_id, inn_raw, mode)
            await update.message.reply_text('ИНН должен содержать 10 или 12 цифр без пробелов.')
            return AWAITING_INN

    logger.info("User %s checking INN %s (mode=%s)", user_id, inn_raw, mode)
    await update.message.reply_text('Ищу информацию, пожалуйста, подождите...')

    info = await fetch_dadata(inn_raw, context.bot_data['dadata_client'])
    if not info:
        logger.info("INN %s not found in DaData (user=%s)", inn_raw, user_id)
        await update.message.reply_text(
            'По указанному ИНН данные не найдены.',
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    if mode == MODE_ORG:
        message = format_org_info(info)
    elif mode == MODE_IP:
        message = format_ip_info(info)
    elif mode == MODE_INDIV:
        message = format_individual_info(info)
    else:  # universal — choose formatter by entity type reported by DaData
        entity_type = (info.get('data') or {}).get('type')
        if entity_type == 'LEGAL' or len(inn_raw) == 10:
            message = format_org_info(info)
        else:
            message = format_ip_info(info)


    return ConversationHandler.END


# ── callback query handlers ───────────────────────────────────────────────────

async def check_another_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text('Выберите режим проверки:', reply_markup=MAIN_KEYBOARD)


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

    async def post_init(app: Application) -> None:
        dadata_token = os.environ.get('DADATA_TOKEN', '')
        dadata_secret = os.environ.get('DADATA_SECRET', '')
        app.bot_data['dadata_client'] = DadataAsync(dadata_token, dadata_secret)

    async def post_shutdown(app: Application) -> None:
        client: DadataAsync = app.bot_data.get('dadata_client')
        if client:
            await client.close()

    app = Application.builder().token(token).post_init(post_init).post_shutdown(post_shutdown).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^🏢 Всё об организации$'), ask_org_inn),
            MessageHandler(filters.Regex(r'^👤 Всё об ИП$'), ask_ip_inn),
            MessageHandler(filters.Regex(r'^🧑 Физлицо$'), ask_indiv_inn),
            MessageHandler(filters.Regex(r'^🔎 Проверить ИНН$'), ask_universal_inn),
        ],
        states={
            AWAITING_INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_inn)],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('help', help_cmd),
        ],
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('feedback', feedback_cmd))
    app.add_handler(CallbackQueryHandler(check_another_callback, pattern=r'^check_another$'))
    app.add_handler(CallbackQueryHandler(feedback_callback, pattern=r'^feedback:'))
    app.add_handler(conv_handler)
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
