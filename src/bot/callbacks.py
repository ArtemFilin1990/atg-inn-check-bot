import logging
from aiogram import Router
from aiogram.types import CallbackQuery

from typing import Optional

from bot.formatters import format_risks
from bot.keyboards import MAIN_KEYBOARD

logger = logging.getLogger(__name__)
router = Router()


async def _get_inn(query: CallbackQuery, sessions) -> Optional[str]:
    inn = await sessions.get_field(query.from_user.id, 'last_inn')
    if not inn:
        await query.answer('Сначала введите ИНН.', show_alert=True)
        return None
    await query.answer()
    return inn


async def _send_pages(query: CallbackQuery, pages: list):
    for page in pages:
        await query.message.answer(page)


@router.callback_query(lambda c: c.data == 'risks')
async def cb_risks(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'risks')
    await _send_pages(query, format_risks(inn, data))


@router.callback_query(lambda c: c.data == 'check_another')
async def cb_check_another(query: CallbackQuery, sessions):
    await query.answer()
    await sessions.set_field(query.from_user.id, 'last_inn', None)
    await query.message.answer('Выберите режим проверки:', reply_markup=MAIN_KEYBOARD)
