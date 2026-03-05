from __future__ import annotations

import logging
from typing import Any

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from app.config import config
from app.dadata_client import find_by_id_party, validate_inn
from app.formatters import format_card

logger = logging.getLogger(__name__)

BTN_CHECK = "🔎 Проверить ИНН"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CHECK)]],
    resize_keyboard=True,
)

WELCOME_TEXT = (
    "Привет! Я бот для проверки компаний по ИНН.\n\n"
    "Нажмите «🔎 Проверить ИНН» или просто отправьте 10 или 12 цифр ИНН."
)


class InnForm(StatesGroup):
    waiting_inn = State()


router = Router()


async def _lookup_and_reply(message: Message, inn: str) -> None:
    if not config.DADATA_API_KEY:
        await message.answer("Ошибка: DADATA_API_KEY не настроен.")
        return

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

    card_text = format_card(suggestions[0])
    await waiting_msg.edit_text(card_text, parse_mode="Markdown")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


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
    await _lookup_and_reply(message, inn)


@router.message(F.text.regexp(r"^\d{10}$|^\d{12}$"))
async def process_inn_direct(message: Message, state: FSMContext) -> None:
    inn = (message.text or "").strip()
    await _lookup_and_reply(message, inn)


@router.message(F.text.regexp(r"^\d+$"))
async def process_digits_invalid(message: Message) -> None:
    await message.answer("Введите ИНН: 10 или 12 цифр, только цифры.")


@router.message()
async def fallback_handler(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp
