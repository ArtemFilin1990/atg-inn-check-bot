from __future__ import annotations

import pytest

from app.main import _build_webhook_url


def test_build_webhook_url_returns_none_for_empty_input() -> None:
    assert _build_webhook_url("") is None
    assert _build_webhook_url("   ") is None


def test_build_webhook_url_strips_trailing_slash() -> None:
    assert _build_webhook_url("https://example.com/") == "https://example.com/tg/webhook"


@pytest.mark.parametrize("value", ["example.com", "ftp://example.com", "https:///only-path"])
def test_build_webhook_url_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        _build_webhook_url(value)
