import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from app.validation import validate_inn


class TestValidateInn(unittest.TestCase):

    # ── valid 10-digit INNs ────────────────────────────────────────────────

    def test_valid_legal_entity(self):
        # Well-known valid INN (Sberbank)
        self.assertTrue(validate_inn("7707083893"))

    def test_valid_legal_entity_2(self):
        # Yandex LLC
        self.assertTrue(validate_inn("7736207543"))

    # ── valid 12-digit INNs ────────────────────────────────────────────────

    def test_valid_individual_12(self):
        # Synthetic valid 12-digit INN
        # Build one programmatically
        inn = _make_valid_12()
        self.assertTrue(validate_inn(inn))

    # ── invalid inputs ────────────────────────────────────────────────────

    def test_invalid_empty(self):
        self.assertFalse(validate_inn(""))

    def test_invalid_letters(self):
        self.assertFalse(validate_inn("770708389X"))

    def test_invalid_length_9(self):
        self.assertFalse(validate_inn("123456789"))

    def test_invalid_length_11(self):
        self.assertFalse(validate_inn("12345678901"))

    def test_invalid_checksum_10(self):
        self.assertFalse(validate_inn("7707083890"))  # last digit wrong

    def test_invalid_checksum_12(self):
        inn = list(_make_valid_12())
        inn[-1] = str((int(inn[-1]) + 1) % 10)
        self.assertFalse(validate_inn("".join(inn)))

    def test_invalid_spaces(self):
        self.assertFalse(validate_inn("770708 3893"))

    def test_invalid_too_long(self):
        self.assertFalse(validate_inn("7707083893123"))


def _make_valid_12() -> str:
    """Construct a synthetic valid 12-digit INN."""
    base = [5, 0, 0, 1, 0, 0, 0, 0, 0, 0]  # 10 base digits
    w11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    w12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    c11 = sum(w * d for w, d in zip(w11, base)) % 11 % 10
    base11 = base + [c11]
    c12 = sum(w * d for w, d in zip(w12, base11)) % 11 % 10
    return "".join(str(d) for d in base11 + [c12])


if __name__ == "__main__":
    unittest.main()
