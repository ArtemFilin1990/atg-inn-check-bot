import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from bot.formatters import validate_inn, _inn_checksum_valid


class TestValidateInn(unittest.TestCase):

    def test_valid_10_digit_inn(self):
        self.assertEqual(validate_inn('7736207543'), '7736207543')

    def test_valid_12_digit_inn(self):
        self.assertEqual(validate_inn('500100732259'), '500100732259')

    def test_valid_13_digit_ogrn(self):
        self.assertEqual(validate_inn('1027700132195'), '1027700132195')

    def test_strips_non_digits(self):
        self.assertEqual(validate_inn('77 3620 7543'), '7736207543')

    def test_too_short(self):
        self.assertIsNone(validate_inn('773620754'))

    def test_too_long_wrong(self):
        self.assertIsNone(validate_inn('1234567890123456'))

    def test_non_digits_only(self):
        self.assertIsNone(validate_inn('hello'))

    def test_empty(self):
        self.assertIsNone(validate_inn(''))

    def test_11_digits_invalid(self):
        self.assertIsNone(validate_inn('12345678901'))


class TestChecksum(unittest.TestCase):

    def test_known_valid_10(self):
        # Sberbank INN
        self.assertTrue(_inn_checksum_valid('7707083893'))

    def test_invalid_10(self):
        self.assertFalse(_inn_checksum_valid('7707083890'))

    def test_known_valid_12(self):
        self.assertTrue(_inn_checksum_valid('500100732259'))

    def test_invalid_12(self):
        self.assertFalse(_inn_checksum_valid('500100732251'))


class TestStrictCheck(unittest.TestCase):
    """Test STRICT_INN_CHECK=true rejects invalid checksums."""

    def setUp(self):
        os.environ['STRICT_INN_CHECK'] = 'true'
        # Reload the module so _STRICT is re-evaluated
        import importlib
        import bot.formatters as fmt
        importlib.reload(fmt)
        from bot.formatters import validate_inn as vi
        self._vi = vi

    def tearDown(self):
        os.environ.pop('STRICT_INN_CHECK', None)
        import importlib
        import bot.formatters as fmt
        importlib.reload(fmt)

    def test_strict_rejects_bad_checksum_10(self):
        self.assertIsNone(self._vi('7707083890'))

    def test_strict_accepts_valid_checksum_10(self):
        self.assertEqual(self._vi('7707083893'), '7707083893')

    def test_strict_rejects_bad_checksum_12(self):
        self.assertIsNone(self._vi('500100732251'))

    def test_strict_accepts_valid_checksum_12(self):
        self.assertEqual(self._vi('500100732259'), '500100732259')

    def test_strict_ogrn_not_checksummed(self):
        # OGRN (13 digits) is not checksum-validated; just length check
        self.assertEqual(self._vi('1027700132195'), '1027700132195')


if __name__ == '__main__':
    unittest.main()
