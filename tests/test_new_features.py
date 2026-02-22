import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from bot.formatters import (
    format_email_result, format_affiliates, format_selfemployed,
    MAX_EMAIL_RESULTS, MAX_AFFILIATES_DISPLAY,
)


class TestFormatEmailResult(unittest.TestCase):
    def test_empty_results(self):
        pages = format_email_result('info@example.com', [])
        self.assertEqual(len(pages), 1)
        self.assertIn('не найдены', pages[0])
        self.assertIn('info@example.com', pages[0])

    def test_with_one_result(self):
        results = [{
            'dadata': {
                'value': 'ООО Ромашка',
                'data': {
                    'inn': '7736207543',
                    'name': {'short_with_opf': 'ООО Ромашка'},
                    'address': {'unrestricted_value': 'г. Москва'},
                },
            },
            'is_individual': False,
            'okved_name': None,
            'inn': '7736207543',
        }]
        pages = format_email_result('info@example.com', results)
        text = '\n'.join(pages)
        self.assertIn('ООО Ромашка', text)
        self.assertIn('7736207543', text)

    def test_html_escaping(self):
        results = [{
            'dadata': {
                'value': '<script>alert(1)</script>',
                'data': {'inn': '1234567890', 'name': {}, 'address': {}},
            },
            'is_individual': False,
            'okved_name': None,
            'inn': '1234567890',
        }]
        pages = format_email_result('x@y.com', results)
        text = '\n'.join(pages)
        self.assertNotIn('<script>', text)
        self.assertIn('&lt;script&gt;', text)

    def test_caps_at_five_results(self):
        results = [
            {'dadata': {'value': f'ООО #{i}', 'data': {'inn': f'{i:010d}', 'name': {}, 'address': {}}},
             'is_individual': False, 'okved_name': None, 'inn': f'{i:010d}'}
            for i in range(10)
        ]
        pages = format_email_result('test@test.com', results)
        text = '\n'.join(pages)
        # Should show at most MAX_EMAIL_RESULTS results
        self.assertIn(f'{MAX_EMAIL_RESULTS})', text)
        self.assertNotIn(f'{MAX_EMAIL_RESULTS + 1})', text)


class TestFormatAffiliates(unittest.TestCase):
    def test_empty(self):
        pages = format_affiliates('7736207543', [])
        self.assertEqual(len(pages), 1)
        self.assertIn('не найдено', pages[0])

    def test_with_affiliates(self):
        affiliates = [
            {
                'value': 'ООО Дочка',
                'data': {
                    'inn': '7737360831',
                    'type': 'LEGAL',
                    'name': {'short_with_opf': 'ООО Дочка'},
                },
            },
            {
                'value': 'ИП Иванов',
                'data': {
                    'inn': '500100732259',
                    'type': 'INDIVIDUAL',
                    'name': {'short_with_opf': 'ИП Иванов'},
                },
            },
        ]
        pages = format_affiliates('7736207543', affiliates)
        text = '\n'.join(pages)
        self.assertIn('ООО Дочка', text)
        self.assertIn('(ЮЛ)', text)
        self.assertIn('ИП Иванов', text)
        self.assertIn('(ИП)', text)

    def test_caps_at_ten(self):
        affiliates = [
            {'value': f'ООО #{i}', 'data': {'inn': f'{i:010d}', 'type': 'LEGAL', 'name': {'short_with_opf': f'ООО #{i}'}}}
            for i in range(15)
        ]
        pages = format_affiliates('1234567890', affiliates)
        text = '\n'.join(pages)
        self.assertIn(f'{MAX_AFFILIATES_DISPLAY})', text)
        self.assertNotIn(f'{MAX_AFFILIATES_DISPLAY + 1})', text)


class TestFormatSelfemployed(unittest.TestCase):
    def test_empty_result(self):
        pages = format_selfemployed('500100732259', {})
        self.assertIn('недоступны', pages[0])

    def test_is_selfemployed(self):
        pages = format_selfemployed('500100732259', {'status': True, 'message': 'является'})
        self.assertIn('✅', pages[0])
        self.assertIn('самозанятый', pages[0])

    def test_not_selfemployed(self):
        pages = format_selfemployed('500100732259', {'status': False, 'message': 'не является'})
        self.assertIn('❌', pages[0])
        self.assertIn('не самозанятый', pages[0])

    def test_unknown_status(self):
        pages = format_selfemployed('500100732259', {'message': 'Ошибка'})
        self.assertIn('Ошибка', pages[0])


if __name__ == '__main__':
    unittest.main()
