from typing import Optional

MAX_LEN = 3500


def _e(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _get(d: dict, *keys, default="—") -> str:
    """Safely traverse nested dict and return string value."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return str(cur) if cur not in (None, "") else default


def format_company_card(suggestion: dict) -> str:
    """Format a DaData suggestion into a human-readable HTML card."""
    data = suggestion.get("data", {})

    name_full = _get(data, "name", "full_with_opf")
    name_short = _get(data, "name", "short_with_opf")
    inn = _get(data, "inn")
    ogrn = _get(data, "ogrn")
    kpp = _get(data, "kpp")
    status = _get(data, "state", "status")
    reg_date_raw = data.get("state", {}) or {}
    reg_date = _get(data, "ogrn_date")
    liquidation_date = _get(data, "state", "liquidation_date")
    address = _get(data, "address", "unrestricted_value")
    mgmt_name = _get(data, "management", "name")
    mgmt_post = _get(data, "management", "post")
    okved = _get(data, "okved")
    okved_type = _get(data, "okved_type")
    employee_count = _get(data, "employee_count")
    capital = _get(data, "finance", "tax_system")
    revenue = _get(data, "finance", "income")
    expense = _get(data, "finance", "expense")

    # Founders
    founders = data.get("founders") or []
    founders_lines = []
    for f in founders[:5]:
        f_name = f.get("name") or f.get("fio", {}).get("source", "")
        f_share = ""
        share = f.get("share", {}) or {}
        if share.get("value"):
            f_share = f" ({share['value']}%)"
        if f_name:
            founders_lines.append(f"  • {_e(f_name)}{_e(f_share)}")

    # Status flag
    is_liquidated = status == "LIQUIDATED"
    status_label = "❌ Ликвидирована" if is_liquidated else "✅ Действующая"

    lines = [
        f"<b>{_e(name_full)}</b>",
        f"Краткое: {_e(name_short)}",
        "",
        f"📋 <b>Реквизиты</b>",
        f"ИНН: <code>{_e(inn)}</code>",
        f"ОГРН: <code>{_e(ogrn)}</code>",
        f"КПП: <code>{_e(kpp)}</code>",
        "",
        f"📅 Дата регистрации (ОГРН): {_e(_format_ts(data.get('ogrn_date')))}",
    ]

    if is_liquidated and liquidation_date != "—":
        lines.append(f"📅 Дата ликвидации: {_e(_format_ts(data.get('state', {}).get('liquidation_date')))}")

    lines += [
        "",
        f"🏢 <b>Адрес</b>: {_e(address)}",
        "",
        f"👤 <b>Руководитель</b>: {_e(mgmt_name)} ({_e(mgmt_post)})",
        "",
        f"🏭 <b>ОКВЭД</b>: {_e(okved)} (тип: {_e(okved_type)})",
        "",
        f"👥 Сотрудников: {_e(employee_count)}",
    ]

    if revenue != "—" or expense != "—":
        lines += [
            "",
            f"💰 <b>Финансы</b>",
            f"Доходы: {_e(revenue)}",
            f"Расходы: {_e(expense)}",
        ]

    if founders_lines:
        lines += ["", "🧑‍💼 <b>Учредители</b>:"] + founders_lines

    lines += ["", f"Статус: {status_label}"]

    card = "\n".join(lines)
    if len(card) > MAX_LEN:
        card = card[:MAX_LEN - 3] + "..."
    return card


def format_requisites(suggestion: dict) -> str:
    """Return plain-text requisites for copying."""
    data = suggestion.get("data", {})
    inn = _get(data, "inn")
    ogrn = _get(data, "ogrn")
    kpp = _get(data, "kpp")
    name = _get(data, "name", "full_with_opf")
    address = _get(data, "address", "unrestricted_value")
    return (
        f"Наименование: {name}\n"
        f"ИНН: {inn}\n"
        f"ОГРН: {ogrn}\n"
        f"КПП: {kpp}\n"
        f"Адрес: {address}"
    )


def format_branch_card(suggestion: dict, index: int, total: int) -> str:
    """Format a branch (filial) card."""
    data = suggestion.get("data", {})
    name = _get(data, "name", "full_with_opf")
    kpp = _get(data, "kpp")
    address = _get(data, "address", "unrestricted_value")
    mgmt_name = _get(data, "management", "name")
    mgmt_post = _get(data, "management", "post")
    status = _get(data, "state", "status")
    status_label = "❌ Ликвидирован" if status == "LIQUIDATED" else "✅ Действует"

    return (
        f"<b>Филиал {index}/{total}</b>\n"
        f"{_e(name)}\n"
        f"КПП: <code>{_e(kpp)}</code>\n"
        f"📍 {_e(address)}\n"
        f"👤 {_e(mgmt_name)} ({_e(mgmt_post)})\n"
        f"Статус: {status_label}"
    )


def _format_ts(ts) -> str:
    """Convert unix-ms timestamp to date string."""
    if ts is None:
        return "—"
    try:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(ts)
