import copy

from app.formatters import (
    format_card,
    format_contacts,
    format_courts,
    format_debts,
    format_founders,
    format_penalties,
    format_requisites,
    format_turnover,
)

FIXTURE_SUGGESTION = {
    "value": "ПАО СБЕРБАНК",
    "data": {
        "inn": "7707083893",
        "ogrn": "1027700132195",
        "kpp": "773601001",
        "name": {
            "short_with_opf": "ПАО Сбербанк",
            "full_with_opf": "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО «СБЕРБАНК РОССИИ»",
        },
        "state": {"status": "ACTIVE", "registration_date": "1991-08-20"},
        "address": {
            "value": "117997, г Москва, ул Вавилова, д 19",
            "data": {"city": "Москва", "street_with_type": "ул Вавилова", "house_type_full": "д", "house": "19"},
        },
        "management": {"name": "Греф Герман Оскарович", "post": "Президент"},
        "okved": "64.19",
        "phones": [{"value": "+7 495 500-55-50"}],
        "emails": [{"value": "info@sberbank.ru"}],
        "founders": [{"name": "ЦБ РФ", "share": {"value": 50, "type": "%"}}],
        "finance": {"year": 2022, "revenue": 1000, "income": 100, "expense": 80, "debt": 12, "penalty": 3},
    },
}


def test_format_card_contains_key_fields():
    text = format_card(FIXTURE_SUGGESTION)
    assert "Сбербанк" in text
    assert "действует" in text
    assert "7707083893" in text


def test_format_card_length_within_limit():
    text = format_card(FIXTURE_SUGGESTION)
    assert len(text) <= 3500


def test_format_card_truncated_long():
    suggestion = copy.deepcopy(FIXTURE_SUGGESTION)
    suggestion["data"]["name"]["short_with_opf"] = "А" * 5000
    text = format_card(suggestion)
    assert len(text) <= 3500
    assert text.endswith("…")


def test_format_requisites_contains_ids():
    text = format_requisites(FIXTURE_SUGGESTION)
    assert "7707083893" in text
    assert "1027700132195" in text


def test_format_contacts_contains_phone_email():
    text = format_contacts(FIXTURE_SUGGESTION)
    assert "495" in text
    assert "sberbank" in text


def test_format_founders_contains_founder():
    text = format_founders(FIXTURE_SUGGESTION)
    assert "ЦБ" in text


def test_format_turnover_contains_finance():
    text = format_turnover(FIXTURE_SUGGESTION)
    assert "Выручка" in text
    assert "1 000" in text


def test_format_debts_contains_debt_penalty():
    text = format_debts(FIXTURE_SUGGESTION)
    assert "Недоимки" in text
    assert "12" in text


def test_format_courts_mentions_provider_for_full_cases():
    text = format_courts(FIXTURE_SUGGESTION)
    assert "провайдера" in text


def test_format_penalties_contains_penalty():
    text = format_penalties(FIXTURE_SUGGESTION)
    assert "Штрафы" in text
    assert "3" in text
