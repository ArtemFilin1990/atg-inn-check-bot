import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from app.validation import validate_inn
from app.dadata_client import DaDataClient
from app.formatters import format_company_card, format_requisites, format_branch_card
from app.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

# ── FSM ──────────────────────────────────────────────────────────────────────

class Form(StatesGroup):
    waiting_for_inn = State()


# ── Keyboards ─────────────────────────────────────────────────────────────────

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏁 Старт"), KeyboardButton(text="👋 Привет")],
        [KeyboardButton(text="🔎 Проверить ИНН")],
    ],
    resize_keyboard=True,
)


def card_inline_kb(inn: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подробнее", callback_data=f"detail:{inn}"),
                InlineKeyboardButton(text="Филиалы", callback_data=f"branches:{inn}:0"),
            ],
            [
                InlineKeyboardButton(
                    text="Скопировать реквизиты", callback_data=f"copy:{inn}"
                )
            ],
        ]
    )


def branches_nav_kb(inn: str, page: int, total: int) -> InlineKeyboardMarkup:
    buttons = []
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="◀️", callback_data=f"branches:{inn}:{page - 1}")
        )
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(
            InlineKeyboardButton(text="▶️", callback_data=f"branches:{inn}:{page + 1}")
        )
    buttons.append(nav)
    buttons.append(
        [InlineKeyboardButton(text="« Назад", callback_data=f"detail:{inn}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_dispatcher(dadata: DaDataClient, limiter: RateLimiter) -> Dispatcher:
    dp = Dispatcher()

    # ── /start ───────────────────────────────────────────────────────────────

    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "Привет! Я помогу проверить компанию по ИНН.\n"
            "Выберите действие:",
            reply_markup=MAIN_KB,
        )

    # ── Reply buttons ────────────────────────────────────────────────────────

    @dp.message(F.text == "🏁 Старт")
    async def btn_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Привет! Выберите действие:", reply_markup=MAIN_KB)

    @dp.message(F.text == "👋 Привет")
    async def btn_hello(message: Message) -> None:
        await message.answer("Привет! 👋 Чем могу помочь?", reply_markup=MAIN_KB)

    @dp.message(F.text == "🔎 Проверить ИНН")
    async def btn_check_inn(message: Message, state: FSMContext) -> None:
        await state.set_state(Form.waiting_for_inn)
        await message.answer(
            "Введите ИНН компании (10 цифр) или ИП (12 цифр):"
        )

    # ── INN input ─────────────────────────────────────────────────────────────

    @dp.message(Form.waiting_for_inn)
    async def handle_inn_input(message: Message, state: FSMContext) -> None:
        await _process_inn(message, state, message.text or "")

    @dp.message(F.text.regexp(r"^\d{10}$|^\d{12}$"))
    async def handle_inn_direct(message: Message, state: FSMContext) -> None:
        await _process_inn(message, state, message.text or "")

    async def _process_inn(message: Message, state: FSMContext, text: str) -> None:
        inn = text.strip()
        if not validate_inn(inn):
            await message.answer(
                "❌ Некорректный ИНН. Введите 10 (юрлицо) или 12 (ИП) цифр."
            )
            return

        await state.clear()
        await limiter.acquire()

        try:
            suggestion = await dadata.find_by_inn(inn)
        except PermissionError as exc:
            await message.answer(f"⛔ Ошибка доступа: {exc}")
            return
        except RuntimeError as exc:
            await message.answer(f"⚠️ {exc}")
            return
        except Exception as exc:
            logger.exception("DaData error")
            await message.answer("❌ Ошибка при запросе к DaData. Попробуйте позже.")
            return

        if suggestion is None:
            await message.answer("🔍 Компания не найдена по данному ИНН.")
            return

        card = format_company_card(suggestion)
        await message.answer(card, parse_mode="HTML", reply_markup=card_inline_kb(inn))

    # ── Inline callbacks ──────────────────────────────────────────────────────

    @dp.callback_query(F.data.startswith("detail:"))
    async def cb_detail(call: CallbackQuery) -> None:
        inn = call.data.split(":", 1)[1]
        await limiter.acquire()
        try:
            suggestion = await dadata.find_by_inn(inn)
        except Exception:
            await call.answer("Ошибка загрузки данных", show_alert=True)
            return
        if suggestion is None:
            await call.answer("Компания не найдена", show_alert=True)
            return
        card = format_company_card(suggestion)
        await call.message.edit_text(
            card, parse_mode="HTML", reply_markup=card_inline_kb(inn)
        )
        await call.answer()

    @dp.callback_query(F.data.startswith("branches:"))
    async def cb_branches(call: CallbackQuery) -> None:
        _, inn, page_str = call.data.split(":", 2)
        page = int(page_str)
        await limiter.acquire()
        try:
            branches = await dadata.get_branches(inn)
        except Exception:
            await call.answer("Ошибка загрузки филиалов", show_alert=True)
            return
        if not branches:
            await call.answer("Филиалы не найдены", show_alert=True)
            return
        total = len(branches)
        branch_card = format_branch_card(branches[page], page + 1, total)
        await call.message.edit_text(
            branch_card,
            parse_mode="HTML",
            reply_markup=branches_nav_kb(inn, page, total),
        )
        await call.answer()

    @dp.callback_query(F.data.startswith("copy:"))
    async def cb_copy(call: CallbackQuery) -> None:
        inn = call.data.split(":", 1)[1]
        await limiter.acquire()
        try:
            suggestion = await dadata.find_by_inn(inn)
        except Exception:
            await call.answer("Ошибка загрузки данных", show_alert=True)
            return
        if suggestion is None:
            await call.answer("Компания не найдена", show_alert=True)
            return
        text = format_requisites(suggestion)
        await call.message.answer(f"<pre>{text}</pre>", parse_mode="HTML")
        await call.answer("Реквизиты отправлены!")

    @dp.callback_query(F.data == "noop")
    async def cb_noop(call: CallbackQuery) -> None:
        await call.answer()

    return dp
