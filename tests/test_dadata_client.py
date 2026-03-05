"""Tests for app.dadata_client: find_by_id_party and validation helpers."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.dadata_client import (
    _cache,
    find_by_id_party,
    find_party_universal,
    suggest_party,
    validate_inn,
)

SAMPLE_RESPONSE = {
    "suggestions": [
        {
            "value": "ПАО Сбербанк",
            "data": {
                "inn": "7707083893",
                "ogrn": "1027700132195",
                "kpp": "773601001",
            },
        }
    ]
}


@pytest.fixture(autouse=True)
def clear_dadata_cache():
    _cache.clear()
    yield
    _cache.clear()


def _make_mock_client(json_data=None, status_code=200, raise_on_status=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if json_data is not None:
        mock_resp.json.return_value = json_data
    if raise_on_status is not None:
        mock_resp.raise_for_status.side_effect = raise_on_status
    else:
        mock_resp.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_client, mock_resp


def test_validate_inn_10_digits():
    assert validate_inn("7707083893") is True


def test_validate_inn_12_digits():
    assert validate_inn("784806113663") is True


def test_validate_inn_empty():
    assert validate_inn("") is False


def test_validate_inn_non_digit():
    assert validate_inn("77070838XX") is False


@pytest.mark.asyncio
async def test_find_by_id_party_returns_suggestions():
    mock_cm, _, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        result = await find_by_id_party("test_key", "7707083893")
    assert result == SAMPLE_RESPONSE


@pytest.mark.asyncio
async def test_find_by_id_party_sends_correct_auth_header():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("my_secret_key", "7707083893")
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Token my_secret_key"


@pytest.mark.asyncio
async def test_find_by_id_party_caches_result():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        r1 = await find_by_id_party("key", "7707083893")
        r2 = await find_by_id_party("key", "7707083893")
    assert mock_client.post.call_count == 1
    assert r1 == r2


@pytest.mark.asyncio
async def test_find_by_id_party_raises_on_timeout():
    mock_cm, mock_client, _ = _make_mock_client()
    mock_client.post.side_effect = httpx.TimeoutException("timed out")
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        with pytest.raises(httpx.TimeoutException):
            await find_by_id_party("key", "7707083893")


@pytest.mark.asyncio
async def test_suggest_party_uses_suggest_endpoint():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await suggest_party("key", "Сбербанк", count=1)
    args, _ = mock_client.post.call_args
    assert "suggest/party" in args[0]


@pytest.mark.asyncio
async def test_find_party_universal_uses_suggest_then_find_by_id():
    suggested = {
        "suggestions": [{"value": "ПАО Сбербанк", "data": {"inn": "7707083893"}}],
    }
    detailed = {"suggestions": [{"value": "ПАО Сбербанк", "data": {"inn": "7707083893", "kpp": "1"}}]}
    with patch("app.dadata_client.suggest_party", new_callable=AsyncMock) as sp, patch(
        "app.dadata_client.find_by_id_party", new_callable=AsyncMock
    ) as fb:
        sp.return_value = suggested
        fb.return_value = detailed
        result = await find_party_universal("key", "ПАО Сбербанк")
    assert result == detailed
    sp.assert_awaited_once()
    fb.assert_awaited_once_with("key", query="7707083893", count=1)


@pytest.mark.asyncio
async def test_find_party_universal_falls_back_to_find_by_id_for_numeric_without_suggest():
    empty = {"suggestions": []}
    with patch("app.dadata_client.suggest_party", new_callable=AsyncMock) as sp, patch(
        "app.dadata_client.find_by_id_party", new_callable=AsyncMock
    ) as fb:
        sp.return_value = empty
        fb.return_value = SAMPLE_RESPONSE
        result = await find_party_universal("key", "7707083893")
    assert result == SAMPLE_RESPONSE
    sp.assert_awaited_once()
    fb.assert_awaited_once_with("key", query="7707083893", count=1)
