import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from bot.formatters import (
    paginate, format_org_card, format_ip_card, format_courts,
    format_debts, format_bankruptcy, _fmt_money, PAGE_LIMIT,
    format_summary_card, format_links_section, format_debt_section, format_court_section, format_json_section,
)


class TestPaginate(unittest.TestCase):
    def test_short_text_no_split(self):
        text = 'Hello world'
        self.assertEqual(paginate(text), ['Hello world'])

    def test_long_text_splits(self):
        line = 'A' * 100 + '\n'
        text = line * 50  # 5100 chars
        pages = paginate(text, limit=3800)
        self.assertGreater(len(pages), 1)
        for page in pages:
            self.assertLessEqual(len(page), 3800)

    def test_no_newline_hard_cut(self):
        text = 'X' * 5000
        pages = paginate(text, limit=3800)
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(pages[0]), 3800)


class TestFmtMoney(unittest.TestCase):
    def test_none(self):
        self.assertEqual(_fmt_money(None), '—')

    def test_integer(self):
        result = _fmt_money(1000000)
        self.assertIn('₽', result)
        self.assertIn('1', result)

    def test_zero(self):
        result = _fmt_money(0)
        self.assertIn('₽', result)


class TestFormatOrgCard(unittest.TestCase):
    def _make_data(self, **overrides):
        base = {
            'dadata': {
                'data': {
                    'inn': '7736207543',
                    'kpp': '773601001',
                    'ogrn': '1027700132195',
                    'name': {'short_with_opf': 'ООО Тест'},
                    'state': {'name': 'Действующая'},
                    'address': {'unrestricted_value': 'г. Москва'},
                    'okved': '62.01',
                },
            },
            'okved_name': None,
            'is_individual': False,
        }
        base.update(overrides)
        return base

    def test_contains_inn(self):
        text = format_org_card(self._make_data())
        self.assertIn('7736207543', text)

    def test_contains_name(self):
        text = format_org_card(self._make_data())
        self.assertIn('ООО Тест', text)

    def test_contains_risks_section(self):
        text = format_org_card(self._make_data())
        self.assertIn('Риски', text)

    def test_empty_data(self):
        # Should not raise
        text = format_org_card({'dadata': {}, 'is_individual': False})
        self.assertIsInstance(text, str)


class TestFormatCourts(unittest.TestCase):
    def test_empty(self):
        pages = format_courts('1234567890', {})
        self.assertEqual(len(pages), 1)
        self.assertIn('не найдено', pages[0])

    def test_with_data(self):
        data = {
            'total': 3, 'plaintiff_pct': 60, 'defendant_pct': 40,
            'cases': [
                {'number': 'A40-1/24', 'court': 'АС МО', 'date': '2024-01-01', 'status': 'Завершено'},
            ]
        }
        pages = format_courts('1234567890', data)
        self.assertGreater(len(pages[0]), 0)
        self.assertIn('A40-1/24', pages[0])


class TestFormatBankruptcy(unittest.TestCase):
    def test_not_found(self):
        pages = format_bankruptcy('123', {'found': False})
        self.assertIn('не найдено', pages[0])

    def test_found(self):
        pages = format_bankruptcy('123', {
            'found': True, 'status': 'банкрот', 'case_number': 'A40-5/24',
            'court': 'АС МО', 'stage': 'конкурсное', 'date': '2024-01-01',
        })
        self.assertIn('A40-5/24', pages[0])


class TestMenuSections(unittest.TestCase):
    def _entity(self):
        return {
            'dadata': {
                'value': 'ООО Тест',
                'data': {
                    'inn': '7736207543',
                    'kpp': '773601001',
                    'ogrn': '1027700132195',
                    'state': {'status': 'ACTIVE'},
                    'address': {'value': 'г. Москва'},
                    'okved': '62.01',
                    'founders': [{'name': 'Иванов И.И.', 'inn': '500100732259'}],
                    'managers': [{'name': 'Петров П.П.', 'post': 'Генеральный директор'}],
                    'finance': {'year': 2023, 'debt': 1000, 'penalty': 50},
                },
            }
        }

    def test_summary_card(self):
        text = format_summary_card(self._entity())
        self.assertIn('ООО Тест', text)
        self.assertIn('ACTIVE', text)

    def test_links_section(self):
        text = format_links_section(self._entity())
        self.assertIn('Учредители', text)
        self.assertIn('Руководители', text)

    def test_debt_section(self):
        text = format_debt_section(self._entity())
        self.assertIn('Недоимки', text)

    def test_court_section_empty(self):
        text = format_court_section(self._entity())
        self.assertIn('COURT не найдены', text)

    def test_json_section_html_pre(self):
        text = format_json_section({'payload': [{'x': '<tag>'}]})
        self.assertTrue(text.startswith('<pre>'))
        self.assertIn('&lt;tag&gt;', text)


if __name__ == '__main__':
    unittest.main()
