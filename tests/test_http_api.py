import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest

from http_api import (
    LookupValidationError,
    parse_lookup_params,
    build_lookup_response,
    SimpleRateLimiter,
    rate_limiter_from_env,
)


class TestParseLookupParams(unittest.TestCase):
    def test_valid_minimal(self):
        query, entity_type, count = parse_lookup_params({'query': '7736207543'})
        self.assertEqual(query, '7736207543')
        self.assertIsNone(entity_type)
        self.assertEqual(count, 10)

    def test_reject_invalid_query(self):
        with self.assertRaises(LookupValidationError):
            parse_lookup_params({'query': 'abc'})

    def test_reject_wrong_entity_type(self):
        with self.assertRaises(LookupValidationError):
            parse_lookup_params({'query': '7736207543', 'entity_type': 'UNKNOWN'})

    def test_reject_legal_with_ip_inn(self):
        with self.assertRaises(LookupValidationError):
            parse_lookup_params({'query': '500100732259', 'entity_type': 'LEGAL'})

    def test_reject_count_out_of_range(self):
        with self.assertRaises(LookupValidationError):
            parse_lookup_params({'query': '7736207543', 'count': 50})

    def test_reject_boolean_count(self):
        with self.assertRaises(LookupValidationError):
            parse_lookup_params({'query': '7736207543', 'count': True})


class TestBuildLookupResponse(unittest.TestCase):
    def test_maps_expected_fields(self):
        card_data = {
            'query': '7736207543',
            'inn': '7736207543',
            'okved_name': 'Разработка программного обеспечения',
            'dadata': {
                'value': 'ООО Ромашка',
                'data': {
                    'inn': '7736207543',
                    'ogrn': '1027700132195',
                    'kpp': '770601001',
                    'type': 'LEGAL',
                    'name': {'short_with_opf': 'ООО Ромашка'},
                    'state': {'status': 'ACTIVE'},
                    'address': {'unrestricted_value': 'г. Москва'},
                    'okved': '62.01',
                },
            },
        }
        result = build_lookup_response(card_data)
        self.assertEqual(result['name'], 'ООО Ромашка')
        self.assertEqual(result['entity_type'], 'LEGAL')
        self.assertEqual(result['okved_name'], 'Разработка программного обеспечения')




class TestRateLimiterFromEnv(unittest.TestCase):
    def test_invalid_env_fallback(self):
        os.environ['LOOKUP_RATE_LIMIT_RPS'] = 'bad'
        limiter = rate_limiter_from_env()
        self.assertTrue(limiter.allow('2.2.2.2'))

    def test_negative_env_becomes_zero(self):
        os.environ['LOOKUP_RATE_LIMIT_RPS'] = '-1'
        limiter = rate_limiter_from_env()
        self.assertTrue(limiter.allow('3.3.3.3'))
        self.assertTrue(limiter.allow('3.3.3.3'))

    def tearDown(self):
        os.environ.pop('LOOKUP_RATE_LIMIT_RPS', None)

class TestSimpleRateLimiter(unittest.TestCase):
    def test_allows_then_rejects_immediately(self):
        limiter = SimpleRateLimiter(requests_per_second=1)
        self.assertTrue(limiter.allow('1.1.1.1'))
        self.assertFalse(limiter.allow('1.1.1.1'))


if __name__ == '__main__':
    unittest.main()
