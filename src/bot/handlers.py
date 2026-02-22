import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.states import InnForm
from bot.keyboards import MAIN_KEYBOARD, NAV_KEYBOARD, ORG_RESULT_KEYBOARD, SIMPLE_RESULT_KEYBOARD
from bot.formatters import validate_inn, format_org_card, format_ip_card, format_individual_card, paginate

logger = logging.getLogger(__name__)

def _pick_card_format(mode: str, query: str, card_data: dict):
    """Return (formatted_text, keyboard) based on mode and entity type."""
    is_individual = card_data.get('is_individual', False)
    entity_type = ((card_data.get('dadata') or {}).get('data') or {}).get('type', '')
    is_legal = entity_type == 'LEGAL' or len(query) == 10

    if mode == MODE_ORG or (mode == MODE_UNIVERSAL and is_legal):
        return format_org_card(card_data), ORG_RESULT_KEYBOARD
    if mode == MODE_IP or (mode == MODE_UNIVERSAL and is_individual):
        return format_ip_card(card_data), SIMPLE_RESULT_KEYBOARD
    if mode == MODE_INDIV:
        return format_individual_card(card_data), SIMPLE_RESULT_KEYBOARD
    # fallback: treat as org
    return format_org_card(card_data), ORG_RESULT_KEYBOARD

MODE_ORG = 'org'
MODE_IP = 'ip'
MODE_INDIV = 'indiv'
MODE_UNIVERSAL = 'universal'

_BTN_ORG = '🏢 1) Всё об организации'
_BTN_IP = '🧑‍💼 2) Всё об ИП'
_BTN_INDIV = '🪪 3) Физлицо'
_BTN_UNIVERSAL = '🔎 Проверить ИНН'
_BTN_BACK = '◀️ Назад'
_BTN_HOME = '🏠 Домой'


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    logger.info("User %s /start", message.from_user.id)
    await state.clear()
    await message.answer(
        '🕵️ Агент на связи. Работаем тихо и без лишнего шума.\n'
        'Только легальные данные из официальных источников.\n\n'
        '🤫 Шёпотом: введи ИНН (10/12 цифр) или выбери режим кнопкой ниже.',
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        'Выберите кнопку для проверки:\n'
        f'{_BTN_ORG} — ИНН из 10 цифр или ОГРН из 13 цифр\n'
        f'{_BTN_IP} — ИНН из 12 цифр\n'
        f'{_BTN_INDIV} — ИНН из 12 цифр\n'
        f'{_BTN_UNIVERSAL} — универсальный режим (10 или 12 цифр)\n\n'
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
    await state.update_data(mode=MODE_ORG)
    logger.info("User %s → mode %s", message.from_user.id, MODE_ORG)
    await message.answer(
        '🏢 Организация\n\nВведи:\n• ИНН (10 цифр) или\n• ОГРН (13 цифр)\n\n'
        'Можно просто вставить число — без пробелов.',
        reply_markup=NAV_KEYBOARD,
    )


@router.message(F.text == _BTN_IP)
async def ask_ip(message: Message, state: FSMContext):
    await state.set_state(InnForm.waiting_inn)
    await state.update_data(mode=MODE_IP)
    logger.info("User %s → mode %s", message.from_user.id, MODE_IP)
    await message.answer('🧑‍💼 Введи ИНН ИП (12 цифр).', reply_markup=NAV_KEYBOARD)


@router.message(F.text == _BTN_INDIV)
async def ask_indiv(message: Message, state: FSMContext):
    await state.set_state(InnForm.waiting_inn)
    await state.update_data(mode=MODE_INDIV)
    logger.info("User %s → mode %s", message.from_user.id, MODE_INDIV)
    await message.answer('🪪 Введи ИНН физлица (12 цифр).', reply_markup=NAV_KEYBOARD)


@router.message(F.text == _BTN_UNIVERSAL)
async def ask_universal(message: Message, state: FSMContext):
    await state.set_state(InnForm.waiting_inn)
    await state.update_data(mode=MODE_UNIVERSAL)
    logger.info("User %s → mode %s", message.from_user.id, MODE_UNIVERSAL)
    await message.answer('🔎 Введи ИНН (10 или 12 цифр).', reply_markup=NAV_KEYBOARD)


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
    if text in (_BTN_ORG, _BTN_IP, _BTN_INDIV, _BTN_UNIVERSAL, _BTN_BACK, _BTN_HOME):
        await state.clear()
        await message.answer('Выберите режим проверки:', reply_markup=MAIN_KEYBOARD)
        return

    data = await state.get_data()
    mode = data.get('mode', MODE_UNIVERSAL)

    query = validate_inn(text)

    # Validate by mode
    if mode == MODE_ORG:
        if not query or len(query) not in (10, 13):
            await message.answer(
                'Не похоже на ИНН/ОГРН.\n'
                'ИНН — 10 цифр, ОГРН — 13 цифр. Без пробелов и букв.'
            )
            return
    elif mode in (MODE_IP, MODE_INDIV):
        if not query or len(query) != 12:
            await message.answer('ИНН должен содержать 12 цифр без пробелов.')
            return
    else:
        if not query or len(query) not in (10, 12):
            await message.answer('ИНН должен содержать 10 или 12 цифр без пробелов.')
            return

    logger.info("User %s checking %s (mode=%s)", user_id, query, mode)
    await message.answer('Ищу по реестрам… 5–10 секунд.')

    card_data = await aggregator.get_card(query)
    if not card_data:
        await message.answer('По указанному ИНН данные не найдены.', reply_markup=MAIN_KEYBOARD)
        await state.clear()
        return

    resolved_inn = card_data.get('inn', query)
    await sessions.set_field(user_id, 'last_inn', resolved_inn)

    text_out, keyboard = _pick_card_format(mode, query, card_data)

    pages = paginate(text_out)
    for i, page in enumerate(pages):
        kb = keyboard if i == len(pages) - 1 else None
        await message.answer(page, reply_markup=kb)

    await state.clear()
