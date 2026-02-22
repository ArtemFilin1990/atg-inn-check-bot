import logging
import json
import re
import time
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.states import InnForm
from bot.keyboards import MAIN_KEYBOARD, NAV_KEYBOARD, ORG_RESULT_KEYBOARD, SIMPLE_RESULT_KEYBOARD
from bot.formatters import validate_inn, format_org_card, format_ip_card, paginate

logger = logging.getLogger(__name__)
router = Router()

_RE_PERSON_FIO = re.compile(r'^[^\d]+$')
_REQUEST_INTERVAL_SECONDS = 1.0
_JSON_CHUNK_SIZE = 3600

MODE_LEGAL = 'LEGAL'
MODE_INDIVIDUAL = 'INDIVIDUAL'
MODE_PERSON = 'PERSON'

_BTN_ORG = '🏢 ООО'
_BTN_IP = '👤 ИП'
_BTN_PERSON = '🧍 Физлицо'
_BTN_BACK = '◀️ Назад'
_BTN_HOME = '🏠 Домой'


def _pick_card_format(mode: str, card_data: dict):
    entity_type = ((card_data.get('dadata') or {}).get('data') or {}).get('type', '')
    if mode == MODE_LEGAL:
        return format_org_card(card_data), ORG_RESULT_KEYBOARD
    if mode == MODE_INDIVIDUAL:
        return format_ip_card(card_data), SIMPLE_RESULT_KEYBOARD
    if entity_type == 'INDIVIDUAL':
        return format_ip_card(card_data), SIMPLE_RESULT_KEYBOARD
    return format_org_card(card_data), ORG_RESULT_KEYBOARD


def _is_valid_person_query(text: str) -> bool:
    words = [w for w in text.split() if w]
    if len(words) < 2 or len(words) > 4:
        return False
    return bool(_RE_PERSON_FIO.match(text))


def _extract_query_for_find_by_id(suggestion: dict) -> str:
    data = suggestion.get('data') or {}
    return data.get('inn') or data.get('ogrn') or ''


def _build_person_keyboard(suggestions: list) -> InlineKeyboardMarkup:
    rows = []
    for i, suggestion in enumerate(suggestions[:10]):
        data = suggestion.get('data') or {}
        value = suggestion.get('value') or 'Без названия'
        inn = data.get('inn') or '—'
        rows.append([InlineKeyboardButton(text=f'{i + 1}) {value} ({inn})', callback_data=f'person_pick:{i}')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _json_pages(suggestions: list) -> list[str]:
    payload = {'suggestions': suggestions}
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    return [raw[i:i + _JSON_CHUNK_SIZE] for i in range(0, len(raw), _JSON_CHUNK_SIZE)] or ['{}']


async def _check_rate_limit(user_id: int, sessions) -> bool:
    now = time.time()
    last_ts = await sessions.get_field(user_id, 'last_request_ts', 0.0)
    if now - float(last_ts or 0.0) < _REQUEST_INTERVAL_SECONDS:
        return False
    await sessions.set_field(user_id, 'last_request_ts', now)
    return True


async def _send_card(message: Message, mode: str, card_data: dict, sessions, user_id: int):
    resolved_inn = card_data.get('inn') or ''
    if resolved_inn:
        await sessions.set_field(user_id, 'last_inn', resolved_inn)

    text_out, keyboard = _pick_card_format(mode, card_data)
    suggestions = card_data.get('suggestions') or []
    if not suggestions and card_data.get('dadata'):
        suggestions = [card_data['dadata']]
    if len(suggestions) > 1:
        text_out += f'\n\nНайдено карточек: {len(suggestions)}'

    pages = paginate(text_out)
    for i, page in enumerate(pages):
        kb = keyboard if i == len(pages) - 1 else None
        await message.answer(page, reply_markup=kb)

    for chunk in _json_pages(suggestions):
        await message.answer(f'```json\n{chunk}\n```', parse_mode=None)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    logger.info("User %s /start", message.from_user.id)
    await state.clear()
    await message.answer(
        '🕵️ Агент на связи. Работаем тихо и без лишнего шума.\n'
        'Только легальные данные из официальных источников.\n\n'
        '🤫 Выберите режим: ООО, ИП или Физлицо.',
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        'Выберите кнопку для проверки:\n'
        f'{_BTN_ORG} — ИНН (10) или ОГРН (13), поиск findById/party с type=LEGAL\n'
        f'{_BTN_IP} — ИНН (12) или ОГРНИП (15), поиск findById/party с type=INDIVIDUAL\n'
        f'{_BTN_PERSON} — ФИО, поиск suggest/party и выбор карточки\n\n'
        'Команда /feedback — отправить предложение.',
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command('feedback'))
async def cmd_feedback(message: Message):
    text = ' '.join(message.text.split()[1:])
    if text:
        logger.info("Feedback from %s: %s", message.from_user.id, text)
        await message.answer('Спасибо за ваш отзыв!')
    else:
        await message.answer('Напишите: /feedback <текст>')


@router.message(F.text == _BTN_ORG)
async def ask_org(message: Message, state: FSMContext):
    await state.set_state(InnForm.waiting_inn)
    await state.update_data(mode=MODE_LEGAL)
    logger.info("User %s → mode %s", message.from_user.id, MODE_LEGAL)
    await message.answer(
        '🏢 ООО / юрлицо\n\nВведи:\n• ИНН (10 цифр) или\n• ОГРН (13 цифр)',
        reply_markup=NAV_KEYBOARD,
    )


@router.message(F.text == _BTN_IP)
async def ask_ip(message: Message, state: FSMContext):
    await state.set_state(InnForm.waiting_inn)
    await state.update_data(mode=MODE_INDIVIDUAL)
    logger.info("User %s → mode %s", message.from_user.id, MODE_INDIVIDUAL)
    await message.answer('👤 ИП\n\nВведи ИНН (12 цифр) или ОГРНИП (15 цифр).', reply_markup=NAV_KEYBOARD)


@router.message(F.text == _BTN_PERSON)
async def ask_person(message: Message, state: FSMContext):
    await state.set_state(InnForm.waiting_inn)
    await state.update_data(mode=MODE_PERSON, person_candidates=[])
    logger.info("User %s → mode %s", message.from_user.id, MODE_PERSON)
    await message.answer('🧍 Физлицо\n\nВведите ФИО (2–4 слова).', reply_markup=NAV_KEYBOARD)


@router.message(F.text == _BTN_HOME)
@router.message(F.text == _BTN_BACK)
async def nav_home(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Выберите режим проверки:', reply_markup=MAIN_KEYBOARD)


@router.message(InnForm.waiting_inn)
async def handle_inn_input(message: Message, state: FSMContext, aggregator, sessions):
    text = message.text.strip()
    user_id = message.from_user.id

    # Allow mode switch from within the waiting state
    if text in (_BTN_ORG, _BTN_IP, _BTN_PERSON, _BTN_BACK, _BTN_HOME):
        await state.clear()
        await message.answer('Выберите режим проверки:', reply_markup=MAIN_KEYBOARD)
        return

    data = await state.get_data()
    mode = data.get('mode', MODE_LEGAL)
    if not await _check_rate_limit(user_id, sessions):
        await message.answer('Слишком часто. Подождите 1 секунду и повторите запрос.')
        return

    if mode == MODE_PERSON:
        if not _is_valid_person_query(text):
            await message.answer('Введите ФИО: 2–4 слова, без цифр.')
            return
        suggestions = await aggregator.dadata.suggest_party(text, count=10)
        if not suggestions:
            await message.answer('По ФИО ничего не найдено. Попробуйте уточнить запрос.')
            return
        await state.update_data(person_candidates=suggestions)
        await message.answer('Выберите найденный вариант:', reply_markup=_build_person_keyboard(suggestions))
        return

    query = validate_inn(text)

    # Validate by mode
    if mode == MODE_LEGAL:
        if not query or len(query) not in (10, 13):
            await message.answer(
                'Не похоже на ИНН/ОГРН.\n'
                'ИНН — 10 цифр, ОГРН — 13 цифр. Без пробелов и букв.'
            )
            return
    elif mode == MODE_INDIVIDUAL:
        if not query or len(query) not in (12, 15):
            await message.answer('ИНН ИП должен быть 12 цифр, ОГРНИП — 15 цифр.')
            return

    logger.info("User %s checking %s (mode=%s)", user_id, query, mode)
    await message.answer('Ищу по реестрам… 5–10 секунд.')

    card_data = await aggregator.get_card(query, entity_type=mode, count=10)
    if not card_data:
        await message.answer('По указанному ИНН данные не найдены.', reply_markup=MAIN_KEYBOARD)
        await state.clear()
        return

    await _send_card(message, mode, card_data, sessions, user_id)

    await state.clear()


@router.callback_query(F.data.startswith('person_pick:'))
async def pick_person_candidate(query: CallbackQuery, state: FSMContext, aggregator, sessions):
    data = await state.get_data()
    candidates = data.get('person_candidates') or []
    try:
        idx = int((query.data or '').split(':', 1)[1])
    except (ValueError, IndexError):
        await query.answer('Некорректный выбор', show_alert=True)
        return
    if idx < 0 or idx >= len(candidates):
        await query.answer('Вариант устарел. Повторите поиск.', show_alert=True)
        return

    user_id = query.from_user.id
    if not await _check_rate_limit(user_id, sessions):
        await query.answer('Слишком часто. Подождите 1 секунду.', show_alert=True)
        return

    suggestion = candidates[idx]
    pick_query = _extract_query_for_find_by_id(suggestion)
    if not pick_query:
        await query.answer('У выбранной записи нет ИНН/ОГРН', show_alert=True)
        return

    await query.answer()
    await query.message.answer('Догружаю полную карточку...')
    card_data = await aggregator.get_card(pick_query, count=10)
    if not card_data:
        await query.message.answer('Полная карточка не найдена.', reply_markup=MAIN_KEYBOARD)
        await state.clear()
        return

    await _send_card(query.message, MODE_PERSON, card_data, sessions, user_id)
    await state.clear()
