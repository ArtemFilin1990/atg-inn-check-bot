import logging
from aiogram import Router
from aiogram.types import CallbackQuery

from typing import Optional

from bot.formatters import (
    format_courts, format_debts, format_checks, format_bankruptcy,
    format_tenders, format_finance, format_connections, format_risks,
)
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


@router.callback_query(lambda c: c.data == 'courts')
async def cb_courts(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'courts')
    await _send_pages(query, format_courts(inn, data))


@router.callback_query(lambda c: c.data == 'debts')
async def cb_debts(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'debts')
    await _send_pages(query, format_debts(inn, data))


@router.callback_query(lambda c: c.data == 'checks')
async def cb_checks(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'checks')
    await _send_pages(query, format_checks(inn, data))


@router.callback_query(lambda c: c.data == 'bankruptcy')
async def cb_bankruptcy(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'bankruptcy')
    await _send_pages(query, format_bankruptcy(inn, data))


@router.callback_query(lambda c: c.data == 'tenders')
async def cb_tenders(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'tenders')
    await _send_pages(query, format_tenders(inn, data))


@router.callback_query(lambda c: c.data == 'finance')
async def cb_finance(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'finance')
    await _send_pages(query, format_finance(inn, data))


@router.callback_query(lambda c: c.data == 'connections')
async def cb_connections(query: CallbackQuery, aggregator, sessions):
    inn = await _get_inn(query, sessions)
    if not inn:
        return
    data = await aggregator.get_section(inn, 'connections')
    await _send_pages(query, format_connections(inn, data))


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
