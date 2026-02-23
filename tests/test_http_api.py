"""Tests for FastAPI endpoints in app.main."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    from app.main import app as _app
    return _app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok_status(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert data.get("status") == "ok"


@pytest.mark.asyncio
async def test_webhook_returns_503_when_bot_not_configured(app):
    """Without a Telegram token the bot object is None → 503."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tg/webhook", json={})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_webhook_returns_400_on_invalid_json(app, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "bot", object())
    monkeypatch.setattr(main.dp, "feed_update", AsyncMock())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/tg/webhook",
            content="{",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_returns_400_on_invalid_update_payload(app, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "bot", object())
    monkeypatch.setattr(main.dp, "feed_update", AsyncMock())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tg/webhook", json={"update_id": "not-int"})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_calls_dispatcher_on_valid_update(app, monkeypatch):
    from app import main

    feed_update = AsyncMock()
    bot_stub = object()
    monkeypatch.setattr(main, "bot", bot_stub)
    monkeypatch.setattr(main.dp, "feed_update", feed_update)

    payload = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1700000000,
            "chat": {"id": 1, "type": "private"},
            "from": {"id": 2, "is_bot": False, "first_name": "Test"},
            "text": "7707083893",
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tg/webhook", json=payload)

    assert response.status_code == 200
    feed_update.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_endpoint_json_content_type(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert "application/json" in response.headers.get("content-type", "")
