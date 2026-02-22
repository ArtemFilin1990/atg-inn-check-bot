import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from bot.handlers import _is_valid_person_query, _extract_query_for_find_by_id, _json_pages


class TestPersonQueryValidation(unittest.TestCase):
    def test_valid_fio(self):
        self.assertTrue(_is_valid_person_query('Иванов Иван Иванович'))

    def test_invalid_fio_with_digits(self):
        self.assertFalse(_is_valid_person_query('Иванов Иван 123'))

    def test_invalid_fio_single_word(self):
        self.assertFalse(_is_valid_person_query('Иванов'))


class TestPersonPickHelpers(unittest.TestCase):
    def test_extract_prefers_inn(self):
        suggestion = {'data': {'inn': '7707083893', 'ogrn': '1027700132195'}}
        self.assertEqual(_extract_query_for_find_by_id(suggestion), '7707083893')

    def test_extract_fallback_ogrn(self):
        suggestion = {'data': {'ogrn': '1027700132195'}}
        self.assertEqual(_extract_query_for_find_by_id(suggestion), '1027700132195')

    def test_json_pages_chunked(self):
        suggestions = [{'value': 'ООО ' + ('X' * 5000), 'data': {'inn': '7707083893'}}]
        pages = _json_pages(suggestions)
        self.assertGreater(len(pages), 1)


if __name__ == '__main__':
    unittest.main()
