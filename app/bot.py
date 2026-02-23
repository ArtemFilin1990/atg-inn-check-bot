from __future__ import annotations

import logging
from typing import Any

import asyncpg

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from app.config import config
from app.dadata_client import find_by_id_party, validate_inn
from app.db import log_request
from app.formatters import format_branch, format_card, format_details, format_requisites
from app.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

BTN_START = "🏁 Старт"
BTN_HELLO = "👋 Привет"
BTN_CHECK = "🔎 Проверить ИНН"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_START), KeyboardButton(text=BTN_HELLO)],
        [KeyboardButton(text=BTN_CHECK)],
    ],
    resize_keyboard=True,
)

WELCOME_TEXT = (
    "Привет! Я бот для проверки компаний по ИНН.\n\n"
    "Нажмите «🔎 Проверить ИНН» или просто отправьте 10 или 12 цифр ИНН."
)


class InnForm(StatesGroup):
    waiting_inn = State()


router = Router()


def _card_inline(inn: str, branch_count: int = 0) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="📋 Подробнее", callback_data=f"details:{inn}"),
            InlineKeyboardButton(text="📋 Скопировать реквизиты", callback_data=f"requisites:{inn}"),
        ]
    ]
    if branch_count > 0:
        buttons.append(
            [InlineKeyboardButton(text=f"🏢 Филиалы ({branch_count})", callback_data=f"branches:{inn}:0")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _lookup_and_reply(message: Message, inn: str) -> None:
    if not config.DADATA_API_KEY:
        await message.answer("Ошибка: DADATA_API_KEY не настроен.")
        return

    if db_pool is not None:
        try:
            await log_request(db_pool, inn)
        except Exception as exc:
            logger.warning("failed to log request to postgres: %s", exc)

    waiting_msg = await message.answer("🔍 Ищу данные…")
    try:
        data = await find_by_id_party(config.DADATA_API_KEY, inn)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 401:
            text = "Ошибка доступа к DaData (ключ)."
        elif code == 403:
            text = "Доступ запрещён/лимит тарифа."
        elif code == 429:
            text = "Слишком много запросов, подождите 10 секунд."
        else:
            text = "Техническая ошибка, попробуйте позже."
        await waiting_msg.edit_text(text)
        return
    except httpx.TimeoutException:
        await waiting_msg.edit_text("DaData не отвечает, попробуйте позже.")
        return
    except Exception as exc:
        logger.exception("unexpected dadata error: %s", exc)
        await waiting_msg.edit_text("Техническая ошибка, попробуйте позже.")
        return

    suggestions: list[dict[str, Any]] = data.get("suggestions", [])
    if not suggestions:
        await waiting_msg.edit_text("Компания не найдена.")
        return

    suggestion = suggestions[0]
    d = suggestion.get("data", {})
    branch_count: int = d.get("branch_count") or 0
    card_text = format_card(suggestion)
    keyboard = _card_inline(inn, branch_count)
    await waiting_msg.edit_text(card_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


@router.message(F.text == BTN_START)
async def btn_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


@router.message(F.text == BTN_HELLO)
async def btn_hello(message: Message) -> None:
    await message.answer("👋 Привет! Отправьте ИНН (10 или 12 цифр) для поиска.")


@router.message(F.text == BTN_CHECK)
async def btn_check(message: Message, state: FSMContext) -> None:
    await state.set_state(InnForm.waiting_inn)
    await message.answer("Введите ИНН (10 или 12 цифр):")


@router.message(InnForm.waiting_inn)
async def process_inn_state(message: Message, state: FSMContext) -> None:
    await state.clear()
    inn = (message.text or "").strip()
    if not validate_inn(inn):
        await message.answer("Введите ИНН: 10 или 12 цифр, только цифры.")
        return
    user_id = message.from_user.id if message.from_user else 0
    if not await check_rate_limit(user_id):
        await message.answer("Слишком много запросов, подождите немного.")
        return
    await _lookup_and_reply(message, inn)


@router.message(F.text.regexp(r"^\d{10}$|^\d{12}$"))
async def process_inn_direct(message: Message, state: FSMContext) -> None:
    inn = (message.text or "").strip()
    user_id = message.from_user.id if message.from_user else 0
    if not await check_rate_limit(user_id):
        await message.answer("Слишком много запросов, подождите немного.")
        return
    await _lookup_and_reply(message, inn)


@router.message(F.text.regexp(r"^\d+$"))
async def process_digits_invalid(message: Message) -> None:
    await message.answer("Введите ИНН: 10 или 12 цифр, только цифры.")


# ── Inline callbacks ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("details:"))
async def cb_details(query: CallbackQuery) -> None:
    inn = (query.data or "").split(":", 1)[1]
    if not config.DADATA_API_KEY:
        await query.answer("DADATA_API_KEY не настроен.", show_alert=True)
        return
    await query.answer()
    try:
        data = await find_by_id_party(config.DADATA_API_KEY, inn)
    except Exception:
        await query.message.answer("Техническая ошибка, попробуйте позже.")
        return
    suggestions = data.get("suggestions", [])
    if not suggestions:
        await query.message.answer("Данные не найдены.")
        return
    text = format_details(suggestions[0])
    await query.message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data.startswith("requisites:"))
async def cb_requisites(query: CallbackQuery) -> None:
    inn = (query.data or "").split(":", 1)[1]
    if not config.DADATA_API_KEY:
        await query.answer("DADATA_API_KEY не настроен.", show_alert=True)
        return
    await query.answer()
    try:
        data = await find_by_id_party(config.DADATA_API_KEY, inn)
    except Exception:
        await query.message.answer("Техническая ошибка, попробуйте позже.")
        return
    suggestions = data.get("suggestions", [])
    if not suggestions:
        await query.message.answer("Данные не найдены.")
        return
    text = format_requisites(suggestions[0])
    await query.message.answer(f"```\n{text}\n```", parse_mode="Markdown")


@router.callback_query(F.data.startswith("branches:"))
async def cb_branches(query: CallbackQuery) -> None:
    parts = (query.data or "").split(":")
    inn = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    if not config.DADATA_API_KEY:
        await query.answer("DADATA_API_KEY не настроен.", show_alert=True)
        return
    await query.answer()
    try:
        data = await find_by_id_party(config.DADATA_API_KEY, inn, branch_type="BRANCH", count=50)
    except Exception:
        await query.message.answer("Техническая ошибка, попробуйте позже.")
        return
    suggestions = data.get("suggestions", [])
    if not suggestions:
        await query.message.answer("Филиалы не найдены.")
        return

    page_size = 5
    total = len(suggestions)
    start = page * page_size
    end = start + page_size
    chunk = suggestions[start:end]

    lines = [f"🏢 *Филиалы* (стр. {page + 1}/{(total + page_size - 1) // page_size})\n"]
    for i, s in enumerate(chunk, start=start + 1):
        lines.append(f"{i}. {format_branch(s)}")
    text = "\n\n".join(lines)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Пред.", callback_data=f"branches:{inn}:{page - 1}")
        )
    if end < total:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️ След.", callback_data=f"branches:{inn}:{page + 1}")
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[nav_buttons]) if nav_buttons else None
    await query.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")



db_pool: asyncpg.Pool[Any] | None = None


def set_db_pool(pool: asyncpg.Pool[Any] | None) -> None:
    global db_pool
    db_pool = pool


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp
