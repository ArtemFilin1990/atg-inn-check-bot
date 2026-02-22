import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from services.aggregator import (
    _parse_courts, _parse_debts, _parse_checks,
    _parse_bankruptcy, _parse_tenders, _parse_finance, _parse_connections,
)


class TestParseCourts(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_parse_courts(None), {})
        self.assertEqual(_parse_courts({}), {'total': 0, 'plaintiff_pct': 0, 'defendant_pct': 0, 'cases': []})

    def test_with_cases(self):
        raw = {'total': 2, 'cases': [{'number': 'A40-1/2024', 'court': 'АС Москвы', 'date': '2024-01-01', 'status': 'active'}]}
        result = _parse_courts(raw)
        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['cases']), 1)
        self.assertEqual(result['cases'][0]['number'], 'A40-1/2024')


class TestParseDebts(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_parse_debts(None), {})

    def test_with_items(self):
        raw = {'total': 1, 'total_sum': 50000, 'items': [{'date': '2024-01-01', 'subject': 'Долг', 'amount': 50000}]}
        result = _parse_debts(raw)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['total_sum'], 50000)


class TestParseBankruptcy(unittest.TestCase):
    def test_not_bankrupt(self):
        result = _parse_bankruptcy({'status': 'ACTIVE'})
        self.assertFalse(result['found'])

    def test_bankrupt(self):
        result = _parse_bankruptcy({'status': 'BANKRUPT', 'bankruptcy': True})
        self.assertTrue(result['found'])

    def test_none(self):
        result = _parse_bankruptcy(None)
        self.assertFalse(result['found'])


class TestParseConnections(unittest.TestCase):
    def test_founders(self):
        raw = {'founders': [{'name': 'Иванов И.И.', 'share': 50}]}
        result = _parse_connections(raw)
        self.assertEqual(len(result['owners']), 1)
        self.assertEqual(result['owners'][0]['name'], 'Иванов И.И.')


if __name__ == '__main__':
    unittest.main()
