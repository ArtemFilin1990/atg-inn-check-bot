import pytest

from app.dadata_client import validate_inn


def test_valid_inn_10():
    assert validate_inn("7707083893") is True


def test_valid_inn_12():
    assert validate_inn("784806113663") is True


def test_invalid_inn_9():
    assert validate_inn("123456789") is False


def test_invalid_inn_11():
    assert validate_inn("12345678901") is False


def test_invalid_inn_13():
    assert validate_inn("1234567890123") is False


def test_invalid_inn_letters():
    assert validate_inn("770708389X") is False


def test_invalid_inn_empty():
    assert validate_inn("") is False


def test_invalid_inn_spaces():
    assert validate_inn("7707 083893") is False
