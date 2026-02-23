import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from app.formatters import format_company_card, format_requisites, format_branch_card, MAX_LEN


def _make_suggestion(overrides: dict = None) -> dict:
    base = {
        "value": "ООО ТЕСТ",
        "unrestricted_value": "ООО ТЕСТ",
        "data": {
            "inn": "7707083893",
            "ogrn": "1027700132195",
            "kpp": "773601001",
            "ogrn_date": 677376000000,
            "name": {
                "full_with_opf": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ ТЕСТ",
                "short_with_opf": "ООО ТЕСТ",
            },
            "state": {
                "status": "ACTIVE",
                "liquidation_date": None,
            },
            "address": {
                "unrestricted_value": "117997, г Москва, ул Вавилова, д 19",
            },
            "management": {
                "name": "Иванов Иван Иванович",
                "post": "Генеральный директор",
            },
            "okved": "64.19",
            "okved_type": "2014",
            "employee_count": None,
            "finance": {
                "tax_system": None,
                "income": None,
                "expense": None,
            },
            "founders": [],
        },
    }
    if overrides:
        base["data"].update(overrides)
    return base


class TestFormatCompanyCard(unittest.TestCase):

    def test_contains_inn(self):
        card = format_company_card(_make_suggestion())
        self.assertIn("7707083893", card)

    def test_contains_ogrn(self):
        card = format_company_card(_make_suggestion())
        self.assertIn("1027700132195", card)

    def test_contains_name(self):
        card = format_company_card(_make_suggestion())
        self.assertIn("ТЕСТ", card)

    def test_active_status(self):
        card = format_company_card(_make_suggestion())
        self.assertIn("✅ Действующая", card)

    def test_liquidated_status(self):
        s = _make_suggestion({"state": {"status": "LIQUIDATED", "liquidation_date": None}})
        card = format_company_card(s)
        self.assertIn("❌ Ликвидирована", card)

    def test_max_length(self):
        # Pad all fields with long text
        long = "А" * 1000
        s = _make_suggestion({"name": {"full_with_opf": long, "short_with_opf": long}})
        card = format_company_card(s)
        self.assertLessEqual(len(card), MAX_LEN)

    def test_html_escaping(self):
        s = _make_suggestion({"name": {"full_with_opf": "<script>alert(1)</script>", "short_with_opf": ""}})
        card = format_company_card(s)
        self.assertNotIn("<script>", card)
        self.assertIn("&lt;script&gt;", card)

    def test_founders_listed(self):
        s = _make_suggestion({
            "founders": [{"name": "Петров П.П.", "share": {"value": "50"}}]
        })
        card = format_company_card(s)
        self.assertIn("Петров", card)

    def test_management_shown(self):
        card = format_company_card(_make_suggestion())
        self.assertIn("Иванов", card)

    def test_address_shown(self):
        card = format_company_card(_make_suggestion())
        self.assertIn("Вавилова", card)


class TestFormatRequisites(unittest.TestCase):

    def test_plain_text(self):
        req = format_requisites(_make_suggestion())
        self.assertIn("ИНН: 7707083893", req)
        self.assertIn("ОГРН: 1027700132195", req)
        self.assertIn("КПП: 773601001", req)

    def test_no_html(self):
        req = format_requisites(_make_suggestion())
        self.assertNotIn("<", req)
        self.assertNotIn(">", req)


class TestFormatBranchCard(unittest.TestCase):

    def test_branch_index(self):
        s = _make_suggestion()
        card = format_branch_card(s, 1, 3)
        self.assertIn("1/3", card)

    def test_branch_active(self):
        s = _make_suggestion()
        card = format_branch_card(s, 1, 1)
        self.assertIn("✅ Действует", card)

    def test_branch_liquidated(self):
        s = _make_suggestion({"state": {"status": "LIQUIDATED", "liquidation_date": None}})
        card = format_branch_card(s, 2, 5)
        self.assertIn("❌ Ликвидирован", card)


if __name__ == "__main__":
    unittest.main()
