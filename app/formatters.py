from __future__ import annotations

from typing import Any

_MARKDOWN_SPECIAL_CHARS = "_*`["
_STATUS_LABELS = {
    "ACTIVE": "действует",
    "LIQUIDATING": "ликвидация",
    "LIQUIDATED": "ликвидирована",
    "BANKRUPT": "банкротство",
    "REORGANIZING": "реорганизация",
}


def _md(text: str) -> str:
    escaped = text
    for char in _MARKDOWN_SPECIAL_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def _s(val: Any, default: str = "") -> str:
    return str(val) if val not in (None, "", {}, []) else default


def _status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status or "—")


def _format_money(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _short_address(data: dict[str, Any]) -> str:
    addr_data = (data.get("address") or {}).get("data") or {}
    city = _s(addr_data.get("city") or addr_data.get("settlement") or addr_data.get("region_with_type"))
    street = _s(addr_data.get("street_with_type"))
    house_num = _s(addr_data.get("house"))
    house_type = _s(addr_data.get("house_type_full"))
    house = " ".join(part for part in [house_type, house_num] if part)
    short = ", ".join(part for part in [city, street, house] if part)
    return short or _s((data.get("address") or {}).get("value"), "—")


def format_card(suggestion: dict[str, Any]) -> str:
    data = suggestion.get("data", {})
    name_obj = data.get("name") or {}
    name = _s(name_obj.get("short_with_opf") or name_obj.get("short") or suggestion.get("value"), "—")

    state = data.get("state") or {}
    lines = [
        f"🏢 *{_md(name)}*",
        f"Статус: *{_md(_status_label(_s(state.get('status'), '—')))}*",
        f"ИНН: `{_md(_s(data.get('inn'), '—'))}` | ОГРН: `{_md(_s(data.get('ogrn'), '—'))}` | КПП: `{_md(_s(data.get('kpp'), '—'))}`",
        f"Регистрация: *{_md(_s(state.get('registration_date'), '—'))}*",
        f"Адрес: {_md(_short_address(data))}",
        f"Руководитель: {_md(_s((data.get('management') or {}).get('name'), '—'))}",
        f"ОКВЭД: `{_md(_s(data.get('okved'), '—'))}`",
    ]
    text = "\n".join(lines)
    return text[:3497] + "…" if len(text) > 3500 else text


def format_requisites(suggestion: dict[str, Any]) -> str:
    data = suggestion.get("data", {})
    name_obj = data.get("name") or {}
    name = _s(name_obj.get("full_with_opf") or name_obj.get("short_with_opf") or suggestion.get("value"), "—")
    lines = [
        f"Наименование: {name.replace('`', "'")}",
        f"ИНН: {_s(data.get('inn'), '—')}",
        f"ОГРН: {_s(data.get('ogrn'), '—')}",
        f"КПП: {_s(data.get('kpp'), '—')}",
        f"Адрес: {_s((data.get('address') or {}).get('value'), '—')}",
    ]
    management = data.get("management") or {}
    if management.get("name"):
        post = _s(management.get("post"))
        post_txt = f" ({post})" if post else ""
        lines.append(f"Руководитель: {_s(management.get('name'))}{post_txt}")
    return "\n".join(lines)


def format_contacts(suggestion: dict[str, Any]) -> str:
    data = suggestion.get("data", {})
    lines = ["📞 *Контакты*"]

    phones = data.get("phones") or []
    if phones:
        lines.append("Телефоны:")
        for phone in phones[:5]:
            lines.append(f"• {_md(_s(phone.get('value'), '—'))}")

    emails = data.get("emails") or []
    if emails:
        lines.append("Email:")
        for email in emails[:5]:
            lines.append(f"• {_md(_s(email.get('value'), '—'))}")

    if len(lines) == 1:
        lines.append("Контакты в DaData не найдены.")
    return "\n".join(lines)


def format_founders(suggestion: dict[str, Any]) -> str:
    data = suggestion.get("data", {})
    founders = data.get("founders") or []
    lines = ["👥 *Учредители*"]
    if not founders:
        lines.append("Данные об учредителях отсутствуют в ответе DaData.")
        return "\n".join(lines)

    for founder in founders[:10]:
        name = _s(founder.get("name") or (founder.get("fio") or {}).get("name") or founder.get("inn"), "—")
        share = founder.get("share") or {}
        value = _s(share.get("value"))
        share_type = _s(share.get("type"))
        suffix = f" — {value} {share_type}".rstrip() if value else ""
        lines.append(f"• {_md(name)}{_md(suffix)}")

    if len(founders) > 10:
        lines.append(f"… и ещё {len(founders) - 10}")
    return "\n".join(lines)


def format_turnover(suggestion: dict[str, Any]) -> str:
    finance = (suggestion.get("data") or {}).get("finance") or {}
    lines = ["💰 *Оборот и финансы*"]
    if not isinstance(finance, dict) or not finance:
        lines.append("Финансовые данные недоступны на текущем тарифе DaData.")
        return "\n".join(lines)

    lines.append(f"Год: {_md(_s(finance.get('year'), '—'))}")
    lines.append(f"Выручка: {_md(_format_money(finance.get('revenue')))}")
    lines.append(f"Доход: {_md(_format_money(finance.get('income')))}")
    lines.append(f"Расходы: {_md(_format_money(finance.get('expense')))}")
    return "\n".join(lines)


def format_debts(suggestion: dict[str, Any]) -> str:
    finance = (suggestion.get("data") or {}).get("finance") or {}
    lines = ["🧾 *Долги и штрафы (DaData)*"]
    if not isinstance(finance, dict) or not finance:
        lines.append("Данные о задолженности недоступны на текущем тарифе DaData.")
        return "\n".join(lines)

    debt = _format_money(finance.get("debt"))
    penalty = _format_money(finance.get("penalty"))
    lines.append(f"Недоимки: {_md(debt)}")
    lines.append(f"Штрафы: {_md(penalty)}")
    return "\n".join(lines)


def format_courts(suggestion: dict[str, Any]) -> str:
    data = suggestion.get("data", {})
    state = data.get("state") or {}
    invalid = data.get("invalid")

    lines = ["⚖️ *Суды и юр-риски (DaData)*"]
    lines.append(f"Юр. статус: {_md(_status_label(_s(state.get('status'), '—')))}")

    if invalid:
        lines.append("Есть отметки о недостоверности сведений в ЕГРЮЛ.")
    else:
        lines.append("Отметки о недостоверности сведений не найдены.")

    lines.append("Полные списки судебных дел требуют отдельного провайдера (Контур/СПАРК/Casebook).")
    return "\n".join(lines)


def format_address(suggestion: dict[str, Any]) -> str:
    address = _s(((suggestion.get("data") or {}).get("address") or {}).get("value"), "—")
    return f"🏢 *Адрес*\n{_md(address)}"


def format_management(suggestion: dict[str, Any]) -> str:
    management = (suggestion.get("data") or {}).get("management") or {}
    name = _s(management.get("name"), "—")
    post = _s(management.get("post"), "—")
    return f"👤 *Руководитель*\n{_md(name)}\nДолжность: {_md(post)}"


def format_okved(suggestion: dict[str, Any]) -> str:
    data = suggestion.get("data", {})
    main = _s(data.get("okved"), "—")
    okveds = data.get("okveds") or []
    lines = ["🧩 *ОКВЭД*", f"Основной: `{_md(main)}`"]
    extras = [o.get("code") for o in okveds if o.get("code")][:10]
    if extras:
        lines.append("Доп.: " + ", ".join(_md(code) for code in extras))
    return "\n".join(lines)


def format_details(suggestion: dict[str, Any]) -> str:
    return format_card(suggestion)


def format_branch(branch: dict[str, Any]) -> str:
    data = branch.get("data", {})
    value = _s(branch.get("value"))
    kpp = _s(data.get("kpp"))
    address = _s((data.get("address") or {}).get("value"))
    parts = [_md(value)]
    if kpp:
        parts.append(f"КПП: {_md(kpp)}")
    if address:
        parts.append(f"📍 {_md(address)}")
    return "\n".join(parts)
