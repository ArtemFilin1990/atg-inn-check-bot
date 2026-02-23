"""Tests for app.rate_limit.check_rate_limit."""
from __future__ import annotations

import asyncio
import pytest

import app.rate_limit as rl


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    """Reset module-level state before each test."""
    rl._user_last.clear()
    yield
    rl._user_last.clear()


@pytest.mark.asyncio
async def test_first_request_allowed():
    assert await rl.check_rate_limit(1) is True


@pytest.mark.asyncio
async def test_immediate_second_request_same_user_denied():
    assert await rl.check_rate_limit(42) is True
    # Same user, no delay → per-user throttle (0.5 s) should reject
    assert await rl.check_rate_limit(42) is False


@pytest.mark.asyncio
async def test_different_users_independent():
    """Two back-to-back requests from *different* users are each allowed
    since the global rate limit has been removed."""
    assert await rl.check_rate_limit(1) is True
    # Different user should not be affected by first user's request
    assert await rl.check_rate_limit(2) is True


@pytest.mark.asyncio
async def test_same_user_allowed_after_per_user_cooldown():
    assert await rl.check_rate_limit(99) is True
    await asyncio.sleep(0.55)  # > 0.5 s per-user interval
    assert await rl.check_rate_limit(99) is True


@pytest.mark.asyncio
async def test_user_last_timestamp_updated_on_allow():
    await rl.check_rate_limit(7)
    assert rl._user_last[7] > 0.0


@pytest.mark.asyncio
async def test_returns_bool():
    result = await rl.check_rate_limit(5)
    assert isinstance(result, bool)
