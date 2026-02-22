import json
import unittest
from unittest.mock import MagicMock, patch

from inn_check_bot.main import dadata_find_party


class DadataFindPartyTests(unittest.TestCase):
    # ── token not configured ─────────────────────────────────────────────────

    @patch.dict('os.environ', {}, clear=True)
    def test_returns_error_when_token_missing(self):
        result = dadata_find_party(query='7707083893')
        self.assertIsInstance(result, dict)
        self.assertIn('error', result)

    # ── parameter filtering ──────────────────────────────────────────────────

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_only_query_sent_when_no_optional_params(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'suggestions': []},
            raise_for_status=lambda: None,
        )
        dadata_find_party(query='7707083893')
        _, kwargs = mock_post.call_args
        payload = json.loads(kwargs['data'].decode('utf-8'))
        self.assertEqual(payload, {'query': '7707083893'})

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_none_optional_params_not_sent(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'suggestions': []},
            raise_for_status=lambda: None,
        )
        dadata_find_party(query='7707083893', count=None, kpp=None,
                          branch_type=None, party_type=None, status=None)
        _, kwargs = mock_post.call_args
        payload = json.loads(kwargs['data'].decode('utf-8'))
        self.assertNotIn('count', payload)
        self.assertNotIn('kpp', payload)
        self.assertNotIn('branch_type', payload)
        self.assertNotIn('type', payload)
        self.assertNotIn('status', payload)

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_all_params_included_when_provided(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'suggestions': [{'value': 'ОАО РЖД'}]},
            raise_for_status=lambda: None,
        )
        dadata_find_party(
            query='7707083893',
            count=1,
            kpp='773601001',
            branch_type='MAIN',
            party_type='LEGAL',
            status=['ACTIVE'],
        )
        _, kwargs = mock_post.call_args
        payload = json.loads(kwargs['data'].decode('utf-8'))
        self.assertEqual(payload['query'], '7707083893')
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['kpp'], '773601001')
        self.assertEqual(payload['branch_type'], 'MAIN')
        self.assertEqual(payload['type'], 'LEGAL')
        self.assertEqual(payload['status'], ['ACTIVE'])

    # ── headers ──────────────────────────────────────────────────────────────

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_correct_headers_sent(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'suggestions': []},
            raise_for_status=lambda: None,
        )
        dadata_find_party(query='7707083893')
        _, kwargs = mock_post.call_args
        headers = kwargs['headers']
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Accept'], 'application/json')
        self.assertEqual(headers['Authorization'], 'Token test_token')

    # ── UTF-8 encoding ────────────────────────────────────────────────────────

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_request_body_is_utf8_bytes(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'suggestions': []},
            raise_for_status=lambda: None,
        )
        dadata_find_party(query='7707083893')
        _, kwargs = mock_post.call_args
        self.assertIsInstance(kwargs['data'], bytes)
        # Verify it's valid UTF-8
        kwargs['data'].decode('utf-8')

    # ── successful return value ───────────────────────────────────────────────

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_returns_suggestions_list_on_success(self, mock_post):
        suggestions = [{'value': 'ОАО РЖД', 'data': {'inn': '7707083893'}}]
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'suggestions': suggestions},
            raise_for_status=lambda: None,
        )
        result = dadata_find_party(query='7707083893')
        self.assertEqual(result, suggestions)

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_returns_empty_list_when_no_suggestions(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'suggestions': []},
            raise_for_status=lambda: None,
        )
        result = dadata_find_party(query='0000000000')
        self.assertEqual(result, [])

    # ── error handling ────────────────────────────────────────────────────────

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post')
    def test_returns_error_on_http_error(self, mock_post):
        import requests as req
        mock_response = MagicMock(status_code=403)
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(
                side_effect=req.HTTPError(response=mock_response)
            )
        )
        result = dadata_find_party(query='7707083893')
        self.assertIsInstance(result, dict)
        self.assertIn('error', result)
        self.assertNotIn('test_token', result.get('error', ''))

    @patch.dict('os.environ', {'DADATA_TOKEN': 'test_token'})
    @patch('inn_check_bot.main.requests.post', side_effect=ConnectionError('network down'))
    def test_returns_error_on_connection_error(self, _mock_post):
        result = dadata_find_party(query='7707083893')
        self.assertIsInstance(result, dict)
        self.assertIn('error', result)
        self.assertNotIn('test_token', result.get('error', ''))


if __name__ == '__main__':
    unittest.main()
