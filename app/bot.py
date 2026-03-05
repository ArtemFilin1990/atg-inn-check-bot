from __future__ import annotations

import logging
import time
from typing import Any

import asyncpg
import httpx
from aiogram import Dispatcher, F, Router
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
from app.dadata_client import find_party_universal, normalize_query_input, validate_inn
from app.db import log_request
from app.formatters import (
    format_card,
    format_contacts,
    format_courts,
    format_debts,
    format_founders,
    format_requisites,
    format_turnover,
)
from app.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

WELCOME_TEXT = "Отправьте ИНН / ОГРН / название — верну короткую карточку и кнопки разделов."
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔎 Проверить")]],
    resize_keyboard=True,
)

CACHE_TTL_SEC = 600
_context_cache: dict[str, dict[str, Any]] = {}


class InnForm(StatesGroup):
    waiting_query = State()


router = Router()


def _cache_set(key: str, value: dict[str, Any]) -> None:
    _context_cache[key] = {"ts": time.time(), "value": value}


def _cache_get(key: str) -> dict[str, Any] | None:
    item = _context_cache.get(key)
    if not item:
        return None
    if time.time() - item["ts"] > CACHE_TTL_SEC:
        _context_cache.pop(key, None)
        return None
    return item["value"]


def _build_context_key(data: dict[str, Any]) -> str:
    inn = (data.get("inn") or "").strip()
    ogrn = (data.get("ogrn") or "").strip()
    return inn or ogrn


def _base_inline(context_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚖️ Суды", callback_data=f"courts:{context_key}"),
                InlineKeyboardButton(text="💰 Оборот", callback_data=f"turnover:{context_key}"),
                InlineKeyboardButton(text="🧾 Долги", callback_data=f"debts:{context_key}"),
            ],
            [
                InlineKeyboardButton(text="📄 Реквизиты", callback_data=f"requisites:{context_key}"),
                InlineKeyboardButton(text="📞 Контакты", callback_data=f"contacts:{context_key}"),
                InlineKeyboardButton(text="👥 Учредители", callback_data=f"founders:{context_key}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Карточка", callback_data=f"card:{context_key}"),
                InlineKeyboardButton(text="🔁 Новый поиск", callback_data="newsearch:0"),
            ],
        ]
    )


def _parse_callback_data(data: str | None, expected_prefix: str) -> str | None:
    expected = f"{expected_prefix}:"
    if not data or not data.startswith(expected):
        return None
    value = data[len(expected) :]
    if not value or not validate_inn(value):
        return None
    return value


def _safe_requisites_code_block(text: str) -> str:
    return text.replace("```", "'''")


async def _lookup_and_reply(message: Message, query_text: str) -> None:
    if not config.DADATA_API_KEY:
        await message.answer("Ошибка: DADATA_API_KEY не настроен.")
        return

    query, query_kind = normalize_query_input(query_text)
    if not query:
        await message.answer("Пришлите ИНН, ОГРН или название компании.")
        return

    if db_pool is not None and query_kind in {"inn", "ogrn"}:
        try:
            await log_request(db_pool, query)
        except Exception as exc:
            logger.warning("failed to log request to postgres: %s", exc)

    waiting_msg = await message.answer("🔍 Ищу данные…")
    try:
        data = await find_party_universal(config.DADATA_API_KEY, query, count=1)
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
        await waiting_msg.edit_text("Ничего не нашёл. Проверьте ИНН/ОГРН или уточните название.")
        return

    suggestion = suggestions[0]
    party = suggestion.get("data", {})
    context_key = _build_context_key(party)
    if not context_key:
        await waiting_msg.edit_text("Не удалось выделить ИНН/ОГРН из ответа DaData.")
        return

    _cache_set(f"party:{context_key}", suggestion)
    await waiting_msg.edit_text(
        format_card(suggestion),
        reply_markup=_base_inline(context_key),
        parse_mode="Markdown",
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


@router.message(F.text)
async def process_query(message: Message, state: FSMContext) -> None:
    await state.clear()
    query = (message.text or "").strip()
    if not query:
        await message.answer("Пришлите ИНН, ОГРН или название компании.")
        return

    user_id = message.from_user.id if message.from_user else 0
    if not await check_rate_limit(user_id):
        await message.answer("Слишком много запросов, подождите немного.")
        return
    await _lookup_and_reply(message, query)


@router.message()
async def fallback_handler(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


@router.callback_query(F.data.startswith("newsearch:"))
async def cb_new_search(query: CallbackQuery) -> None:
    await query.answer()
    if query.message is not None:
        await query.message.answer("Ок. Пришлите новый ИНН/ОГРН/название.")


@router.callback_query(F.data.regexp(r"^(card|courts|turnover|debts|requisites|contacts|founders):"))
async def cb_sections(query: CallbackQuery) -> None:
    raw = query.data or ""
    action, context_key = raw.split(":", 1)
    party = _cache_get(f"party:{context_key}")

    if party is None:
        await query.answer("Кэш истёк", show_alert=True)
        if query.message is not None:
            await query.message.answer("Кэш истёк. Пришлите ИНН/ОГРН/название заново.")
        return

    await query.answer()
    if query.message is None:
        return

    if action == "card":
        text = format_card(party)
    elif action == "courts":
        text = format_courts(party)
    elif action == "turnover":
        text = format_turnover(party)
    elif action == "debts":
        text = format_debts(party)
    elif action == "contacts":
        text = format_contacts(party)
    elif action == "founders":
        text = format_founders(party)
    elif action == "requisites":
        requisites = _safe_requisites_code_block(format_requisites(party))
        text = f"```\n{requisites}\n```"
    else:
        text = "Неизвестный раздел."

    await query.message.edit_text(
        text,
        reply_markup=_base_inline(context_key),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("details:"))
async def cb_details_legacy(query: CallbackQuery) -> None:
    inn = _parse_callback_data(query.data, "details")
    if inn is None:
        await query.answer("Некорректные данные кнопки.", show_alert=True)
        return
    party = _cache_get(f"party:{inn}")
    await query.answer()
    if query.message is not None and party is not None:
        await query.message.edit_text(
            format_card(party),
            reply_markup=_base_inline(inn),
            parse_mode="Markdown",
        )


db_pool: asyncpg.Pool[Any] | None = None


def set_db_pool(pool: asyncpg.Pool[Any] | None) -> None:
    global db_pool
    db_pool = pool


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp
