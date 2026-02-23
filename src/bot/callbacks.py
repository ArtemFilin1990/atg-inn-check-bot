import logging
import time
from typing import Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.formatters import (
    format_summary_card,
    format_links_section,
    format_debt_section,
    format_court_section,
    format_json_section,
)
from bot.keyboards import MAIN_KEYBOARD, MORE_SECTIONS_KEYBOARD, ORG_RESULT_KEYBOARD, section_keyboard

logger = logging.getLogger(__name__)
router = Router()
_MENU_TTL_SECONDS = 24 * 3600


def _build_entity_from_menu(menu: dict) -> Optional[dict]:
    payload = menu.get('payload') or []
    if not payload:
        return None
    idx = menu.get('selected_main_idx') or 0
    if idx >= len(payload):
        idx = 0
    return {'payload': payload, 'dadata': payload[idx]}

def _require_entity(menu: dict) -> Optional[dict]:
    entity = _build_entity_from_menu(menu)
    if not entity:
        return None
    return entity


async def _get_menu_cache(query: CallbackQuery, sessions) -> Optional[dict]:
    menu = await sessions.get_field(query.from_user.id, 'menu_cache', {})
    if not menu or (time.time() - float(menu.get('saved_at') or 0)) > _MENU_TTL_SECONDS:
        await query.answer('Кэш устарел. Выполните новый поиск.', show_alert=True)
        return None
    return menu


async def _edit(query: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    await query.answer()
    await query.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == 'sec:links')
async def cb_links(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    entity = _require_entity(menu)
    if not entity:
        await query.answer('Нет данных в кеше. Выполните новый поиск.', show_alert=True)
        return
    await _edit(query, format_links_section(entity), section_keyboard())


@router.callback_query(F.data == 'sec:debt')
async def cb_debt(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    entity = _require_entity(menu)
    if not entity:
        await query.answer('Нет данных в кеше. Выполните новый поиск.', show_alert=True)
        return
    await _edit(query, format_debt_section(entity), section_keyboard())


@router.callback_query(F.data == 'sec:court')
async def cb_court(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    entity = _require_entity(menu)
    if not entity:
        await query.answer('Нет данных в кеше. Выполните новый поиск.', show_alert=True)
        return
    await _edit(query, format_court_section(entity), section_keyboard())


@router.callback_query(F.data == 'sec:more')
async def cb_more(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    await _edit(query, 'Выберите дополнительный раздел:', MORE_SECTIONS_KEYBOARD)


@router.callback_query(F.data.in_({'sec:fin', 'sec:docs', 'sec:auth', 'sec:okved'}))
async def cb_cached_sections(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    entity = _require_entity(menu)
    if not entity:
        await query.answer('Нет данных в кеше. Выполните новый поиск.', show_alert=True)
        return
    dd = (entity.get('dadata') or {}).get('data') or {}
    mapping = {
        'sec:fin': ('📊 Финансы', dd.get('finance')),
        'sec:docs': ('📄 Лицензии/документы', {'documents': dd.get('documents'), 'licenses': dd.get('licenses')}),
        'sec:auth': ('🏛 Органы', dd.get('authorities')),
        'sec:okved': ('🧾 ОКВЭД', {'okved': dd.get('okved'), 'okveds': dd.get('okveds')}),
    }
    title, payload = mapping[query.data]
    await _edit(query, f'{title}\n{payload if payload else "Нет данных"}', section_keyboard(back='sec:more'))


@router.callback_query(F.data == 'sec:json')
async def cb_json(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    entity = _require_entity(menu)
    if not entity:
        await query.answer('Нет данных в кеше. Выполните новый поиск.', show_alert=True)
        return
    await _edit(query, format_json_section(entity), section_keyboard())


@router.callback_query(F.data == 'sec:aff')
async def cb_affiliates(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    entity = _require_entity(menu)
    if not entity:
        await query.answer('Нет данных в кеше. Выполните новый поиск.', show_alert=True)
        return
    dd = (entity.get('dadata') or {}).get('data') or {}

    options = []
    for role, key in (('FOUNDERS', 'founders'), ('MANAGERS', 'managers')):
        for person in (dd.get(key) or [])[:10]:
            inn = person.get('inn')
            if not inn:
                continue
            options.append((role, inn, person.get('name') or person.get('fio') or inn))

    if not options:
        await _edit(query, '🧬 Аффилированные\nНет учредителей/руководителей с ИНН.', section_keyboard(back='sec:more'))
        return

    keyboard_rows = [[InlineKeyboardButton(text=f'{name} ({inn})', callback_data=f'affpick:{role}:{inn}')]
                     for role, inn, name in options[:10]]
    keyboard_rows.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='sec:more')])
    await _edit(query, 'По кому искать аффилированных?', InlineKeyboardMarkup(inline_keyboard=keyboard_rows))


@router.callback_query(F.data.startswith('affpick:'))
async def cb_affiliates_pick(query: CallbackQuery, aggregator, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    try:
        _, scope, inn = (query.data or '').split(':', 2)
    except ValueError:
        await query.answer('Некорректный выбор', show_alert=True)
        return
    affiliated = await aggregator.dadata.find_affiliated(inn=inn, scope=scope, count=20)
    lines = [f'🧬 Аффилированные по {inn} ({scope})']
    for i, item in enumerate(affiliated[:20], 1):
        dd = item.get('data') or {}
        name = (dd.get('name') or {}).get('short_with_opf') or item.get('value') or '—'
        lines.append(f'{i}) {name} — {dd.get("inn") or "—"}')
    if len(lines) == 1:
        lines.append('Не найдено.')
    await _edit(query, '\n'.join(lines), section_keyboard(back='sec:more'))


@router.callback_query(F.data == 'nav:back')
async def cb_back(query: CallbackQuery, sessions):
    menu = await _get_menu_cache(query, sessions)
    if not menu:
        return
    entity = _require_entity(menu)
    if not entity:
        await query.answer('Нет данных в кеше. Выполните новый поиск.', show_alert=True)
        return
    await _edit(query, format_summary_card(entity), ORG_RESULT_KEYBOARD)


@router.callback_query(F.data == 'nav:new')
async def cb_new(query: CallbackQuery, sessions):
    await query.answer()
    await sessions.set_field(query.from_user.id, 'menu_cache', None)
    await query.message.answer('Выберите режим проверки:', reply_markup=MAIN_KEYBOARD)


@router.callback_query(F.data == 'check_another')
async def cb_check_another(query: CallbackQuery, sessions):
    await query.answer()
    await sessions.set_field(query.from_user.id, 'last_inn', None)
    await sessions.set_field(query.from_user.id, 'menu_cache', None)
    await query.message.answer('Выберите режим проверки:', reply_markup=MAIN_KEYBOARD)
