import copy

from app.formatters import format_card, format_details, format_requisites

# Minimal fixture matching DaData findById/party response structure
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
        "state": {
            "status": "ACTIVE",
            "registration_date": "1991-08-20",
            "actuality_date": "2023-01-01",
        },
        "address": {
            "value": "117997, г Москва, ул Вавилова, д 19",
            "data": {"qc_geo": "0", "qc": "0"},
        },
        "management": {
            "name": "Греф Герман Оскарович",
            "post": "Президент, Председатель Правления",
        },
        "okved": "64.19",
        "okved_type": "2014",
        "okveds": [
            {"code": "64.92", "main": False},
            {"code": "66.19", "main": False},
            {"code": "64.91", "main": False},
            {"code": "65.12", "main": False},
        ],
        "employee_count": 270000,
        "finance": {
            "year": 2022,
            "revenue": 123456789,
            "income": 9876543,
            "expense": 98765432,
        },
        "founders": [
            {
                "name": "Центральный банк РФ",
                "share": {"value": 52.32, "type": "%"},
            },
        ],
        "branch_count": 12,
        "invalid": None,
    },
}


def test_format_card_contains_inn():
    text = format_card(FIXTURE_SUGGESTION)
    assert "7707083893" in text


def test_format_card_contains_name():
    text = format_card(FIXTURE_SUGGESTION)
    assert "Сбербанк" in text


def test_format_card_contains_address():
    text = format_card(FIXTURE_SUGGESTION)
    assert "Москва" in text


def test_format_card_contains_okved():
    text = format_card(FIXTURE_SUGGESTION)
    assert "64.19" in text


def test_format_card_length_within_limit():
    text = format_card(FIXTURE_SUGGESTION)
    assert len(text) <= 3500


def test_format_card_invalid_flag():
    suggestion = dict(FIXTURE_SUGGESTION)
    suggestion["data"] = dict(FIXTURE_SUGGESTION["data"])
    suggestion["data"]["invalid"] = True
    text = format_card(suggestion)
    assert "Недостоверные" in text


def test_format_card_no_invalid_flag():
    text = format_card(FIXTURE_SUGGESTION)
    assert "Недостоверные" not in text


def test_format_card_founders():
    text = format_card(FIXTURE_SUGGESTION)
    assert "Центральный банк" in text


def test_format_card_management():
    text = format_card(FIXTURE_SUGGESTION)
    assert "Греф" in text


def test_format_details():
    text = format_details(FIXTURE_SUGGESTION)
    assert "Подробности" in text


def test_format_requisites():
    text = format_requisites(FIXTURE_SUGGESTION)
    assert "7707083893" in text
    assert "СБЕРБАНК" in text


def test_format_card_address_qc_warning():
    suggestion = copy.deepcopy(FIXTURE_SUGGESTION)
    suggestion["data"]["address"]["data"]["qc_geo"] = "1"
    text = format_card(suggestion)
    assert "требует проверки" in text


def test_format_card_truncated_long():
    suggestion = copy.deepcopy(FIXTURE_SUGGESTION)
    # Create very long name to force truncation
    suggestion["data"]["name"]["short_with_opf"] = "А" * 4000
    text = format_card(suggestion)
    assert len(text) <= 3500
    assert text.endswith("…")
