"""Tests for FastAPI endpoints in app.main."""
from __future__ import annotations

import pytest
import httpx
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
async def test_health_endpoint_json_content_type(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert "application/json" in response.headers.get("content-type", "")
