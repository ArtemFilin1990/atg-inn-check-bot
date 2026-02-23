"""Tests for app.dadata_client: find_by_id_party and validate_inn."""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.dadata_client import find_by_id_party, validate_inn, _cache


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
    """Return a mock httpx.AsyncClient context manager."""
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


# ── validate_inn ─────────────────────────────────────────────────────────────

def test_validate_inn_10_digits():
    assert validate_inn("7707083893") is True


def test_validate_inn_12_digits():
    assert validate_inn("784806113663") is True


def test_validate_inn_empty():
    assert validate_inn("") is False


def test_validate_inn_non_digit():
    assert validate_inn("77070838XX") is False


def test_validate_inn_9_digits():
    assert validate_inn("123456789") is False


def test_validate_inn_11_digits():
    assert validate_inn("12345678901") is False


# ── find_by_id_party: success ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_by_id_party_returns_suggestions():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        result = await find_by_id_party("test_key", "7707083893")
    assert result == SAMPLE_RESPONSE
    assert result["suggestions"][0]["data"]["inn"] == "7707083893"


@pytest.mark.asyncio
async def test_find_by_id_party_sends_correct_auth_header():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("my_secret_key", "7707083893")
    _, kwargs = mock_client.post.call_args
    headers = kwargs.get("headers", {})
    assert headers.get("Authorization") == "Token my_secret_key"


@pytest.mark.asyncio
async def test_find_by_id_party_sends_correct_payload():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("key", "1234567890", branch_type="BRANCH", count=20)
    _, kwargs = mock_client.post.call_args
    payload = kwargs.get("json", {})
    assert payload["query"] == "1234567890"
    assert payload["branch_type"] == "BRANCH"
    assert payload["count"] == 20


@pytest.mark.asyncio
async def test_find_by_id_party_includes_kpp_when_provided():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("key", "7707083893", kpp="773601001")
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["kpp"] == "773601001"


@pytest.mark.asyncio
async def test_find_by_id_party_excludes_kpp_when_none():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("key", "7707083893")
    _, kwargs = mock_client.post.call_args
    assert "kpp" not in kwargs["json"]


@pytest.mark.asyncio
async def test_find_by_id_party_includes_entity_type_when_provided():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("key", "7707083893", entity_type="LEGAL")
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["type"] == "LEGAL"


@pytest.mark.asyncio
async def test_find_by_id_party_excludes_entity_type_when_none():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("key", "7707083893")
    _, kwargs = mock_client.post.call_args
    assert "type" not in kwargs["json"]


# ── find_by_id_party: caching ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_by_id_party_caches_result():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        r1 = await find_by_id_party("key", "7707083893")
        r2 = await find_by_id_party("key", "7707083893")
    # HTTP should be called only once
    assert mock_client.post.call_count == 1
    assert r1 == r2


@pytest.mark.asyncio
async def test_find_by_id_party_different_queries_not_shared():
    mock_cm, mock_client, _ = _make_mock_client(json_data=SAMPLE_RESPONSE)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        await find_by_id_party("key", "7707083893")
        await find_by_id_party("key", "1234567890")
    assert mock_client.post.call_count == 2


# ── find_by_id_party: HTTP error propagation ─────────────────────────────────

@pytest.mark.asyncio
async def test_find_by_id_party_raises_on_401():
    err_resp = httpx.Response(401, request=httpx.Request("POST", "http://x"))
    exc = httpx.HTTPStatusError("401", request=err_resp.request, response=err_resp)
    mock_cm, _, _ = _make_mock_client(raise_on_status=exc)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await find_by_id_party("bad_key", "7707083893")
    assert exc_info.value.response.status_code == 401


@pytest.mark.asyncio
async def test_find_by_id_party_raises_on_429():
    err_resp = httpx.Response(429, request=httpx.Request("POST", "http://x"))
    exc = httpx.HTTPStatusError("429", request=err_resp.request, response=err_resp)
    mock_cm, _, _ = _make_mock_client(raise_on_status=exc)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await find_by_id_party("key", "7707083893")
    assert exc_info.value.response.status_code == 429


@pytest.mark.asyncio
async def test_find_by_id_party_raises_on_timeout():
    mock_cm, mock_client, _ = _make_mock_client()
    mock_client.post.side_effect = httpx.TimeoutException("timed out")
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        with pytest.raises(httpx.TimeoutException):
            await find_by_id_party("key", "7707083893")


@pytest.mark.asyncio
async def test_find_by_id_party_does_not_cache_on_error():
    err_resp = httpx.Response(500, request=httpx.Request("POST", "http://x"))
    exc = httpx.HTTPStatusError("500", request=err_resp.request, response=err_resp)
    mock_cm, mock_client, _ = _make_mock_client(raise_on_status=exc)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        with pytest.raises(httpx.HTTPStatusError):
            await find_by_id_party("key", "7707083893")
    # Cache should be empty — a retry must hit the network
    assert len(_cache) == 0


@pytest.mark.asyncio
async def test_find_by_id_party_empty_suggestions():
    empty = {"suggestions": []}
    mock_cm, _, _ = _make_mock_client(json_data=empty)
    with patch("app.dadata_client.httpx.AsyncClient", return_value=mock_cm):
        result = await find_by_id_party("key", "0000000000")
    assert result["suggestions"] == []
