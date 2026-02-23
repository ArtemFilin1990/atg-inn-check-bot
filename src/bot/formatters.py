import html
import os
import re
from datetime import datetime, timezone
from typing import Optional

_RE_NON_DIGITS = re.compile(r'\D')
_STRICT = os.environ.get('STRICT_INN_CHECK', '').lower() == 'true'
PAGE_LIMIT = 3800  # chars per Telegram message window
MAX_EMAIL_RESULTS = 5
MAX_AFFILIATES_DISPLAY = 10
MAX_SECTION_LINES = 10


def _e(v) -> str:
    """HTML-escape a dynamic value for safe use in HTML parse-mode messages."""
    if v is None:
        return '—'
    return html.escape(str(v))


def validate_inn(text: str) -> Optional[str]:
    """Return cleaned INN/OGRN digits or None if invalid."""
    raw = _RE_NON_DIGITS.sub('', text)
    if not raw.isdigit():
        return None
    if len(raw) not in (10, 12, 13, 15):
        return None
    if _STRICT and len(raw) in (10, 12):
        if not _inn_checksum_valid(raw):
            return None
    return raw


def _inn_checksum_valid(inn: str) -> bool:
    """Verify INN check digit(s). Works for 10-digit (org) and 12-digit (individual/IP)."""
    d = [int(c) for c in inn]

    def ws(digits, weights):
        return sum(x * w for x, w in zip(digits, weights)) % 11 % 10

    if len(inn) == 10:
        return ws(d[:9], [2, 4, 10, 3, 5, 9, 4, 6, 8]) == d[9]
    # 12-digit
    c11 = ws(d[:10], [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
    c12 = ws(d[:11], [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
    return c11 == d[10] and c12 == d[11]


def _fmt_date(ts_ms: Optional[int]) -> str:
    if ts_ms is None:
        return '—'
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%d.%m.%Y')
    except Exception:
        return '—'


def _fmt_money(value) -> str:
    if value is None:
        return '—'
    try:
        return f'{int(value):,}'.replace(',', '\u202f') + ' ₽'  # \u202f = narrow no-break space
    except Exception:
        return str(value)


def paginate(text: str, limit: int = PAGE_LIMIT) -> list:
    """Split text into pages of at most `limit` chars, breaking on newlines."""
    if len(text) <= limit:
        return [text]
    pages = []
    while text:
        if len(text) <= limit:
            pages.append(text)
            break
        cut = text.rfind('\n', 0, limit)
        if cut <= 0:
            cut = limit
        pages.append(text[:cut])
        text = text[cut:].lstrip('\n')
    return pages


def format_org_card(data: dict) -> str:
    """Format organisation main card from aggregated data."""
    dadata = data.get('dadata') or {}
    dd = dadata.get('data') or {}

    name = (
        (dd.get('name') or {}).get('short_with_opf')
        or (dd.get('name') or {}).get('full_with_opf')
        or dadata.get('unrestricted_value') or '—'
    )
    inn = dd.get('inn') or '—'
    kpp = dd.get('kpp') or '—'
    ogrn = dd.get('ogrn') or '—'

    state = dd.get('state') or {}
    status = state.get('name') or state.get('status') or '—'

    reg_date = _fmt_date(state.get('registration_date'))

    address = (dd.get('address') or {}).get('unrestricted_value') or '—'

    mgmt = dd.get('management') or {}
    ceo = '—'
    if isinstance(mgmt, dict):
        ceo_name = mgmt.get('name') or mgmt.get('fio')
        ceo_post = mgmt.get('post') or mgmt.get('position') or ''
        if ceo_name:
            ceo = f'{ceo_post} {ceo_name}'.strip() if ceo_post else ceo_name
    elif isinstance(mgmt, list) and mgmt:
        m = mgmt[0]
        ceo = m.get('fio') or m.get('name') or '—'

    okved_code = dd.get('okved') or '—'
    okved_name = data.get('okved_name') or '—'
    okved_str = f'{okved_code} — {okved_name}' if okved_name != '—' else okved_code

    capital_val = (dd.get('capital') or {}).get('value')
    capital = _fmt_money(capital_val)

    finance = dd.get('finance') or {}
    tax = finance.get('tax_system') or '—'

    # Risks
    status_upper = (state.get('status') or '').upper()
    if status_upper in ('LIQUIDATED', 'BANKRUPT'):
        risk_unreliable = '⛔ да'
    elif status_upper in ('LIQUIDATING', 'REORGANIZING'):
        risk_unreliable = '⚠️ да'
    else:
        risk_unreliable = 'нет'

    return (
        f'🏢 {_e(name)}\n'
        f'Статус: {_e(status)}\n\n'
        f'ИНН/КПП: {inn} / {kpp}\n'
        f'ОГРН: {ogrn}\n'
        f'Дата регистрации: {reg_date}\n'
        f'Адрес (ЕГРЮЛ): {_e(address)}\n'
        f'Руководитель: {_e(ceo)}\n'
        f'ОКВЭД: {_e(okved_str)}\n'
        f'УК: {capital}\n'
        f'Налогообложение: {_e(tax)}\n\n'
        f'⚠️ Риски (сводка):\n'
        f'• Массовый адрес: —\n'
        f'• Массовый руководитель: —\n'
        f'• Недостоверность: {risk_unreliable}'
    )


def format_ip_card(data: dict) -> str:
    dadata = data.get('dadata') or {}
    dd = dadata.get('data') or {}

    name = (
        dadata.get('value')
        or (dd.get('name') or {}).get('full') or '—'
    )
    inn = dd.get('inn') or '—'
    ogrn = dd.get('ogrn') or '—'

    state = dd.get('state') or {}
    status = state.get('name') or state.get('status') or '—'
    reg_date = _fmt_date(state.get('registration_date'))

    address = (dd.get('address') or {}).get('unrestricted_value') or '—'
    okved = dd.get('okved') or '—'

    status_upper = (state.get('status') or '').upper()
    risk = ''
    if status_upper == 'LIQUIDATED':
        risk = '\n⛔ ИП прекратил деятельность'
    elif status_upper == 'LIQUIDATING':
        risk = '\n⚠️ ИП в процессе ликвидации'

    return (
        f'🧑‍💼 ИП: {_e(name)}\n'
        f'Статус: {_e(status)}\n\n'
        f'ИНН: {inn}\n'
        f'ОГРНИП: {ogrn}\n'
        f'Дата регистрации: {reg_date}\n'
        f'Регион: {_e(address)}\n'
        f'ОКВЭД: {_e(okved)}'
        f'{risk}'
    )


def format_individual_card(data: dict) -> str:
    dadata = data.get('dadata') or {}
    dd = dadata.get('data') or {}
    inn = dd.get('inn') or '—'
    state = dd.get('state') or {}
    status = state.get('name') or state.get('status') or '—'
    address = (dd.get('address') or {}).get('unrestricted_value') or '—'
    return (
        f'🪪 Физлицо\n'
        f'ИНН: {inn}\n'
        f'Статус в налоговой: {_e(status)}\n'
        f'Регион регистрации: {_e(address)}'
    )


def format_courts(inn: str, data: dict) -> list:
    cases = data.get('cases') or []
    if not cases:
        return [f'⚖️ Суды по {inn}: сведений не найдено.']
    total = data.get('total') or len(cases)
    plaintiff_pct = data.get('plaintiff_pct', 0)
    defendant_pct = data.get('defendant_pct', 0)
    lines = [
        f'⚖️ Суды по {inn}',
        f'',
        f'Всего дел: {total}',
        f'Роли: истец {plaintiff_pct}% / ответчик {defendant_pct}%',
        f'',
        f'Последние дела:',
    ]
    for i, c in enumerate(cases[:10], 1):
        num = c.get('number') or c.get('case_id') or '—'
        court = c.get('court') or '—'
        date = c.get('date') or '—'
        status = c.get('status') or '—'
        amount = _fmt_money(c.get('amount')) if c.get('amount') else '—'
        lines.append(f'{i}) {_e(num)} — {_e(court)} — {date} — {_e(status)} — {amount}')
    return paginate('\n'.join(lines))


def format_debts(inn: str, data: dict) -> list:
    items = data.get('items') or []
    if not items:
        return [f'💸 Долги / ФССП по {inn}: не найдено.']
    total = data.get('total') or len(items)
    total_sum = _fmt_money(data.get('total_sum'))
    lines = [
        f'💸 Долги / ФССП по {inn}',
        f'',
        f'Исполнительные производства: {total}',
        f'Общая сумма: {total_sum}',
        f'',
        f'Последние:',
    ]
    for i, item in enumerate(items[:10], 1):
        date = item.get('date') or '—'
        subject = item.get('subject') or '—'
        amount = _fmt_money(item.get('amount')) if item.get('amount') else '—'
        region = item.get('region') or '—'
        lines.append(f'{i}) {date} — {_e(subject)} — {amount} — {_e(region)}')
    return paginate('\n'.join(lines))


def format_checks(inn: str, data: dict) -> list:
    items = data.get('items') or []
    total = data.get('total') or len(items)
    lines = [f'🧾 Проверки по {inn}', f'', f'Найдено: {total}']
    if items:
        lines.append('')
        lines.append('Последние:')
        for i, item in enumerate(items[:10], 1):
            kind = item.get('type') or item.get('kind') or '—'
            period = item.get('period') or item.get('date') or '—'
            result = item.get('result') or '—'
            lines.append(f'{i}) {_e(kind)} — {period} — результат: {_e(result)}')
    return paginate('\n'.join(lines))


def format_bankruptcy(inn: str, data: dict) -> list:
    if not data or not data.get('found'):
        return [f'🏦 Банкротство по {inn}: признаков не найдено.']
    status = data.get('status') or '—'
    case_num = data.get('case_number') or '—'
    court = data.get('court') or '—'
    stage = data.get('stage') or '—'
    date = data.get('date') or '—'
    text = (
        f'🏦 Банкротство по {inn}\n\n'
        f'Статус: {_e(status)}\n'
        f'Дело: {_e(case_num)}\n'
        f'Суд: {_e(court)}\n'
        f'Процедура: {_e(stage)} (с {date})'
    )
    return [text]


def format_tenders(inn: str, data: dict) -> list:
    items = data.get('items') or []
    total = data.get('total') or len(items)
    total_sum = _fmt_money(data.get('total_sum'))
    lines = [
        f'🏛 Госзакупки по {inn}',
        f'',
        f'Контрактов: {total}',
        f'Сумма: {total_sum}',
    ]
    if items:
        lines.append('')
        lines.append('Последние:')
        for i, item in enumerate(items[:10], 1):
            num = item.get('number') or item.get('id') or '—'
            date = item.get('date') or '—'
            amount = _fmt_money(item.get('amount')) if item.get('amount') else '—'
            customer = item.get('customer') or '—'
            lines.append(f'{i}) {_e(num)} — {date} — {amount} — {_e(customer)}')
    return paginate('\n'.join(lines))


def format_finance(inn: str, data: dict) -> list:
    rows = data.get('rows') or []
    if not rows:
        return [f'📊 Финансы по {inn}\n\nДанные не найдены.']
    lines = [f'📊 Финансы по {inn}', '']
    lines.append('Выручка:')
    for row in rows[:4]:
        year = row.get('year') or '—'
        rev = _fmt_money(row.get('revenue'))
        lines.append(f'• {year}: {rev}')
    lines.append('')
    lines.append('Чистая прибыль:')
    for row in rows[:4]:
        year = row.get('year') or '—'
        profit = _fmt_money(row.get('net_profit') or row.get('profit'))
        lines.append(f'• {year}: {profit}')
    return paginate('\n'.join(lines))


def format_connections(inn: str, data: dict) -> list:
    owners = data.get('owners') or []
    related = data.get('related') or []
    lines = [f'📎 Связи по {inn}', '']
    if owners:
        lines.append('Учредители:')
        for o in owners[:5]:
            name = o.get('name') or o.get('fio') or '—'
            share = o.get('share') or o.get('percent') or '—'
            lines.append(f'• {_e(name)} — {share}%')
    if related:
        lines.append('')
        lines.append('Связанные компании:')
        for i, r in enumerate(related[:5], 1):
            rname = r.get('name') or '—'
            rinn = r.get('inn') or '—'
            role = r.get('role') or '—'
            lines.append(f'{i}) {_e(rname)} — {rinn} — роль: {_e(role)}')
    if not owners and not related:
        lines.append('Данные не найдены.')
    return paginate('\n'.join(lines))


def format_email_result(email: str, results: list) -> list:
    """Format company search results by email."""
    if not results:
        return [f'📧 По email {_e(email)}: компании не найдены.']
    lines = [f'📧 Поиск по email: {_e(email)}', '']
    for i, r in enumerate(results[:MAX_EMAIL_RESULTS], 1):
        dd = (r.get('dadata') or {}).get('data') or {}
        name = (
            (dd.get('name') or {}).get('short_with_opf')
            or (r.get('dadata') or {}).get('value') or '—'
        )
        inn = dd.get('inn') or '—'
        address = (dd.get('address') or {}).get('unrestricted_value') or '—'
        lines.append(f'{i}) {_e(name)}\n   ИНН: {inn}\n   {_e(address)}')
    return paginate('\n'.join(lines))


def format_affiliates(inn: str, affiliates: list) -> list:
    """Format affiliated companies list."""
    if not affiliates:
        return [f'📎 Аффилированные по {inn}: не найдено.']
    lines = [f'📎 Аффилированные компании ({inn}):', '']
    for i, a in enumerate(affiliates[:MAX_AFFILIATES_DISPLAY], 1):
        dd = a.get('data') or {}
        name = (
            (dd.get('name') or {}).get('short_with_opf')
            or a.get('value') or '—'
        )
        a_inn = dd.get('inn') or '—'
        a_type = dd.get('type') or ''
        type_label = ' (ЮЛ)' if a_type == 'LEGAL' else ' (ИП)' if a_type == 'INDIVIDUAL' else ''
        lines.append(f'{i}) {_e(name)}{type_label}\n   ИНН: {a_inn}')
    return paginate('\n'.join(lines))


def format_selfemployed(inn: str, result: dict) -> list:
    """Format self-employed (самозанятый) check result."""
    if not result:
        return [f'🔍 Самозанятый {inn}: данные недоступны.']
    status = result.get('status')
    if status is True:
        text = (
            f'✅ {inn} — самозанятый\n\n'
            f'Является плательщиком налога на профессиональный доход (НПД).'
        )
    elif status is False:
        text = (
            f'❌ {inn} — не самозанятый\n\n'
            f'Не является плательщиком НПД.'
        )
    else:
        text = f'🔍 Самозанятый {inn}: {_e(result.get("message", "Статус неизвестен"))}'
    return [text]


def format_risks(inn: str, data: dict) -> list:
    state_status = (data.get('state_status') or '').upper()
    if state_status in ('LIQUIDATED', 'BANKRUPT'):
        risk_unreliable = '⛔ да'
        risk_bankrupt = '⛔ да' if state_status == 'BANKRUPT' else 'нет'
    elif state_status in ('LIQUIDATING', 'REORGANIZING'):
        risk_unreliable = '⚠️ да'
        risk_bankrupt = 'нет'
    else:
        risk_unreliable = 'нет'
        risk_bankrupt = 'нет'

    text = (
        f'⚠️ Риски по {inn}\n\n'
        f'• Массовый адрес: —\n'
        f'• Массовый руководитель: —\n'
        f'• Недостоверность: {risk_unreliable}\n'
        f'• Банкротство: {risk_bankrupt}\n'
        f'• ФССП: {data.get("fssp_risk") or "—"}\n'
        f'• Судебная активность: {data.get("court_risk") or "—"}'
    )
    return [text]


def format_summary_card(data: dict) -> str:
    dadata = data.get('dadata') or {}
    dd = dadata.get('data') or {}
    name = dadata.get('value') or dadata.get('unrestricted_value') or '—'
    inn = dd.get('inn') or '—'
    kpp = dd.get('kpp')
    ogrn = dd.get('ogrn') or dd.get('ogrnip')
    status = ((dd.get('state') or {}).get('status')) or '—'
    address = ((dd.get('address') or {}).get('value') or (dd.get('address') or {}).get('unrestricted_value') or '—')
    okved = dd.get('okved') or '—'
    branch_count = dd.get('branch_count')

    ids = [f'ИНН: {inn}']
    if kpp:
        ids.append(f'КПП: {kpp}')
    if ogrn:
        ids.append(f'ОГРН: {ogrn}')
    lines = [
        f'🏷 {_e(name)}',
        ' / '.join(ids),
        f'Статус: {_e(status)}',
        f'Адрес: {_e(address)}',
        f'ОКВЭД: {_e(okved)}',
    ]
    if branch_count is not None:
        lines.append(f'Филиалов: {branch_count}')
    return '\n'.join(lines)


def format_links_section(data: dict) -> str:
    dd = (data.get('dadata') or {}).get('data') or {}
    lines = ['🔗 Связи']
    founders = dd.get('founders') or []
    managers = dd.get('managers') or []
    predecessors = dd.get('predecessors') or []
    successors = dd.get('successors') or []
    if founders:
        lines.append('Учредители:')
        for f in founders[:MAX_SECTION_LINES]:
            lines.append(f"• {_e(f.get('name') or f.get('fio') or '—')} ({f.get('inn') or 'ИНН —'})")
    if managers:
        lines.append('Руководители:')
        for m in managers[:MAX_SECTION_LINES]:
            lines.append(f"• {_e(m.get('name') or m.get('fio') or '—')} ({m.get('post') or 'роль —'})")
    if predecessors:
        lines.append('Правопредшественники:')
        for p in predecessors[:MAX_SECTION_LINES]:
            lines.append(f"• {_e(p.get('name') or '—')} ({p.get('inn') or 'ИНН —'})")
    if successors:
        lines.append('Правопреемники:')
        for s in successors[:MAX_SECTION_LINES]:
            lines.append(f"• {_e(s.get('name') or '—')} ({s.get('inn') or 'ИНН —'})")
    if dd.get('branch_type') or dd.get('branch_count') is not None:
        lines.append(f"Филиальность: {dd.get('branch_type') or '—'}, count={dd.get('branch_count') or 0}")
    if len(lines) == 1:
        lines.append('Данные не заполнены.')
    return '\n'.join(lines)


def format_debt_section(data: dict) -> str:
    finance = ((data.get('dadata') or {}).get('data') or {}).get('finance') or {}
    if not finance:
        return '💰 Долги\nУ источника нет данных / не заполнено.'
    return '\n'.join([
        '💰 Долги',
        f"Год: {finance.get('year') or '—'}",
        f"Недоимки: {_fmt_money(finance.get('debt'))}",
        f"Штрафы: {_fmt_money(finance.get('penalty'))}",
        f"Доходы: {_fmt_money(finance.get('income') or finance.get('revenue'))}",
        f"Расходы: {_fmt_money(finance.get('expense'))}",
    ])


def _court_decisions(entity: dict) -> list[str]:
    invalidity = entity.get('invalidity') or {}
    if invalidity.get('code') != 'COURT':
        return []
    decision = invalidity.get('decision') or {}
    return [f"{decision.get('court_name') or 'Суд —'} / №{decision.get('number') or '—'} / {decision.get('date') or '—'}"]


def format_court_section(data: dict) -> str:
    dd = (data.get('dadata') or {}).get('data') or {}
    lines = ['⚖️ Суды', f"Статус: {(dd.get('state') or {}).get('status') or '—'}"]
    found = []
    for founder in dd.get('founders') or []:
        found.extend(_court_decisions(founder))
    for manager in dd.get('managers') or []:
        found.extend(_court_decisions(manager))
    address = dd.get('address') or {}
    found.extend(_court_decisions(address))
    if found:
        lines.append('Судебные решения (COURT):')
        lines.extend(f'• {x}' for x in found[:MAX_SECTION_LINES])
    else:
        lines.append('Решения COURT не найдены.')
    return '\n'.join(lines)


def format_json_section(data: dict) -> str:
    import json
    payload = data.get('payload') or {}
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    # Bot default parse mode is HTML; return as escaped <pre> block.
    return f'<pre>{_e(raw[:3500])}</pre>'
