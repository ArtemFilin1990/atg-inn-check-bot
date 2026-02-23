from __future__ import annotations

import importlib

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app import bot as bot_module
from app.dadata_client import find_by_id_party
from app.formatters import format_card


@pytest.fixture(autouse=True)
def reset_main_bot_state() -> None:
    from app import main

    main.bot = None


@pytest.mark.asyncio
async def test_find_by_id_party_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError):
        await find_by_id_party("", "7707083893")


@pytest.mark.asyncio
async def test_find_by_id_party_rejects_empty_query() -> None:
    with pytest.raises(ValueError):
        await find_by_id_party("key", "")


@pytest.mark.asyncio
async def test_find_by_id_party_rejects_non_positive_count() -> None:
    with pytest.raises(ValueError):
        await find_by_id_party("key", "7707083893", count=0)


@pytest.mark.asyncio
async def test_find_by_id_party_rejects_non_dict_json() -> None:
    from unittest.mock import MagicMock

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = []

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_client
    cm.__aexit__.return_value = False

    with patch("app.dadata_client.httpx.AsyncClient", return_value=cm):
        with pytest.raises(ValueError):
            await find_by_id_party("key", "7707083893")


def test_format_card_escapes_markdown() -> None:
    suggestion = {"value": "ACME", "data": {"name": {"short_with_opf": "OOO *A_[`"}, "inn": "7707083893"}}
    text = format_card(suggestion)
    assert "*OOO \\*A\\_\\[\\`*" in text


@pytest.mark.asyncio
async def test_fallback_handler_replies_with_welcome() -> None:
    from unittest.mock import AsyncMock

    from app.bot import MAIN_KEYBOARD, WELCOME_TEXT, fallback_handler

    message = AsyncMock()
    await fallback_handler(message)
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.call_args
    assert args[0] == WELCOME_TEXT
    assert kwargs.get("reply_markup") is MAIN_KEYBOARD


def test_parse_callback_data_validates_prefix_and_inn() -> None:
    assert bot_module._parse_callback_data("details:7707083893", "details") == "7707083893"
    assert bot_module._parse_callback_data("details:abc", "details") is None
    assert bot_module._parse_callback_data("oops:7707083893", "details") is None


def test_safe_requisites_code_block_breaks_fences() -> None:
    assert "```" not in bot_module._safe_requisites_code_block("line ``` content")


def test_invalid_postgres_port_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_PORT", "invalid")
    import app.config as cfg

    importlib.reload(cfg)
    assert cfg.config.POSTGRES_PORT == 5432


@pytest.mark.asyncio
async def test_webhook_handles_json_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.main import app
    from app import main

    monkeypatch.setattr(main, "bot", object())
    monkeypatch.setattr(main.dp, "feed_update", AsyncMock())

    async def raise_value_error(self):
        raise ValueError("bad")

    monkeypatch.setattr("starlette.requests.Request.json", raise_value_error)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tg/webhook", content="{}", headers={"content-type": "application/json"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_lifespan_strips_trailing_slash_from_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main

    bot_stub = AsyncMock()
    bot_stub.set_webhook = AsyncMock()
    bot_stub.session.close = AsyncMock()

    monkeypatch.setattr(main.config, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(main.config, "WEBHOOK_URL", "https://example.com/")
    monkeypatch.setattr(main, "Bot", lambda token: bot_stub)
    monkeypatch.setattr(main, "postgres_enabled", lambda: False)

    async with main.lifespan(main.app):
        pass

    bot_stub.set_webhook.assert_awaited_once_with("https://example.com/tg/webhook")
