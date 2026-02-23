from __future__ import annotations

from typing import Any


_MARKDOWN_SPECIAL_CHARS = "_*`["


def _md(text: str) -> str:
    """Escape Telegram Markdown special chars in dynamic user/API text."""
    escaped = text
    for char in _MARKDOWN_SPECIAL_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def _s(val: Any, default: str = "") -> str:
    """Return str(val) or default if val is None/empty."""
    return str(val) if val not in (None, "", {}, []) else default


def format_card(suggestion: dict[str, Any]) -> str:
    """
    Build a compact company card string (≤ 3500 chars) from a DaData suggestion.
    """
    data = suggestion.get("data", {})
    value = suggestion.get("value", "")

    name_obj = data.get("name") or {}
    name = _s(name_obj.get("short_with_opf")) or _s(value)

    inn = _s(data.get("inn"))
    ogrn = _s(data.get("ogrn"))
    kpp = _s(data.get("kpp"))

    state = data.get("state") or {}
    status = _s(state.get("status"))
    reg_date = _s(state.get("registration_date"))
    act_date = _s(state.get("actuality_date"))

    addr_obj = data.get("address") or {}
    address = _s(addr_obj.get("value"))
    addr_flags = []
    addr_data = addr_obj.get("data") or {}
    if str(addr_data.get("qc_geo", "0")) != "0":
        addr_flags.append("требует проверки (qc_geo)")
    if str(addr_data.get("qc", "0")) != "0":
        addr_flags.append("требует проверки (qc)")

    mgmt = data.get("management") or {}
    mgmt_name = _s(mgmt.get("name"))
    mgmt_post = _s(mgmt.get("post"))

    # OKVEDs
    okved_main = _s(data.get("okved"))
    okved_type = _s(data.get("okved_type"))
    okveds_list = data.get("okveds") or []

    employee_count = data.get("employee_count")

    finance_list = data.get("finance") or {}
    # finance can be a single dict or absent
    finance_year = _s(finance_list.get("year") if isinstance(finance_list, dict) else None)
    finance_revenue = _s(finance_list.get("revenue") if isinstance(finance_list, dict) else None)
    finance_income = _s(finance_list.get("income") if isinstance(finance_list, dict) else None)
    finance_expense = _s(finance_list.get("expense") if isinstance(finance_list, dict) else None)

    founders_list = data.get("founders") or []
    invalid = data.get("invalid")

    lines = []
    lines.append(f"🏢 *{_md(name)}*")
    lines.append("")

    id_parts = []
    if inn:
        id_parts.append(f"ИНН: `{_md(inn)}`")
    if ogrn:
        id_parts.append(f"ОГРН: `{_md(ogrn)}`")
    if kpp:
        id_parts.append(f"КПП: `{_md(kpp)}`")
    if id_parts:
        lines.append(" | ".join(id_parts))

    status_line = f"Статус: {_md(status)}" if status else ""
    if reg_date:
        status_line += f" | Регистрация: {_md(reg_date)}"
    if act_date:
        status_line += f" | Актуальность: {_md(act_date)}"
    if status_line:
        lines.append(status_line)

    if address:
        addr_str = f"📍 {_md(address)}"
        if addr_flags:
            addr_str += f" ⚠️ {', '.join(addr_flags)}"
        lines.append(addr_str)

    if mgmt_name:
        post_str = f" ({mgmt_post})" if mgmt_post else ""
        lines.append(f"👤 {_md(mgmt_name)}{_md(post_str)}")

    if okved_main:
        okved_label = f" ({okved_type})" if okved_type else ""
        lines.append(f"ОКВЭД: {_md(okved_main)}{_md(okved_label)}")
    extra_okveds = [o.get("code", "") for o in okveds_list if o.get("main") is not True][:3]
    if extra_okveds:
        lines.append("  Доп.: " + ", ".join(_md(code) for code in extra_okveds))

    if employee_count is not None:
        lines.append(f"Сотрудников: {_md(str(employee_count))}")

    if isinstance(finance_list, dict) and any(
        [finance_year, finance_revenue, finance_income, finance_expense]
    ):
        lines.append("📊 Финансы:")
        if finance_year:
            lines.append(f"  Год: {_md(finance_year)}")
        if finance_revenue:
            lines.append(f"  Выручка: {_md(finance_revenue)}")
        if finance_income:
            lines.append(f"  Доход: {_md(finance_income)}")
        if finance_expense:
            lines.append(f"  Расходы: {_md(finance_expense)}")

    if founders_list:
        lines.append("👥 Учредители:")
        for i, f in enumerate(founders_list[:5]):
            f_name = _s(f.get("name") or (f.get("fio") or {}).get("name") or f.get("inn"))
            share = f.get("share") or {}
            share_val = _s(share.get("value"))
            share_type = _s(share.get("type"))
            share_str = f" — {share_val} {share_type}".rstrip() if share_val else ""
            lines.append(f"  • {_md(f_name)}{_md(share_str)}")
        if len(founders_list) > 5:
            lines.append(f"  и ещё {len(founders_list) - 5}…")

    if invalid:
        lines.append("⚠️ Недостоверные сведения в ЕГРЮЛ")

    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3497] + "…"
    return text


def format_details(suggestion: dict[str, Any]) -> str:
    """Second screen: authorities, documents, phones, emails."""
    data = suggestion.get("data", {})
    lines = ["📋 *Подробности*", ""]

    authorities = data.get("authorities") or {}
    fts_reg = (authorities.get("fts_registration") or {}).get("name")
    pf = (authorities.get("pf") or {}).get("name")
    ifns = (authorities.get("ifns_fl") or authorities.get("ifns") or {}).get("name")
    if fts_reg:
        lines.append(f"ФНС (регистрация): {_md(_s(fts_reg))}")
    if ifns:
        lines.append(f"ИФНС: {_md(_s(ifns))}")
    if pf:
        lines.append(f"ПФР: {_md(_s(pf))}")

    docs = data.get("documents") or {}
    fts_doc = docs.get("fts_registration") or {}
    series = _s(fts_doc.get("series"))
    number = _s(fts_doc.get("number"))
    issue_date = _s(fts_doc.get("issue_date"))
    if series or number:
        lines.append(f"Свидетельство: {_md(series)} {_md(number)} от {_md(issue_date)}".strip())

    phones = data.get("phones") or []
    if phones:
        lines.append("📞 Телефоны:")
        for p in phones[:3]:
            lines.append(f"  • {_md(_s(p.get('value')))}")

    emails = data.get("emails") or []
    if emails:
        lines.append("✉️ Email:")
        for e in emails[:3]:
            lines.append(f"  • {_md(_s(e.get('value')))}")

    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3497] + "…"
    return text


def format_branch(branch: dict[str, Any]) -> str:
    """One branch entry."""
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


def _code_safe(text: str) -> str:
    return text.replace("`", "'")


def format_requisites(suggestion: dict[str, Any]) -> str:
    """Copy-paste block of requisites."""
    data = suggestion.get("data", {})
    name_obj = data.get("name") or {}
    name = _s(name_obj.get("full_with_opf") or name_obj.get("short_with_opf") or suggestion.get("value"))
    inn = _s(data.get("inn"))
    ogrn = _s(data.get("ogrn"))
    kpp = _s(data.get("kpp"))
    address = _s((data.get("address") or {}).get("value"))
    mgmt = data.get("management") or {}
    mgmt_name = _s(mgmt.get("name"))
    mgmt_post = _s(mgmt.get("post"))

    lines = [
        f"Наименование: {_code_safe(name)}",
        f"ИНН: {_code_safe(inn)}",
    ]
    if ogrn:
        lines.append(f"ОГРН: {_code_safe(ogrn)}")
    if kpp:
        lines.append(f"КПП: {_code_safe(kpp)}")
    if address:
        lines.append(f"Адрес: {_code_safe(address)}")
    if mgmt_name:
        post_str = f" ({mgmt_post})" if mgmt_post else ""
        lines.append(f"Руководитель: {_code_safe(mgmt_name + post_str)}")
    return "\n".join(lines)
