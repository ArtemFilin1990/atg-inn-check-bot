"""Tests for app.rate_limit.check_rate_limit."""
from __future__ import annotations

import asyncio
import pytest

import app.rate_limit as rl


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    """Reset module-level state before each test."""
    rl._user_last.clear()
    rl._global_last = 0.0
    yield
    rl._user_last.clear()
    rl._global_last = 0.0


@pytest.mark.asyncio
async def test_first_request_allowed():
    assert await rl.check_rate_limit(1) is True


@pytest.mark.asyncio
async def test_immediate_second_request_same_user_denied():
    assert await rl.check_rate_limit(42) is True
    # Same user, no delay → per-user throttle (0.5 s) should reject
    assert await rl.check_rate_limit(42) is False


@pytest.mark.asyncio
async def test_different_users_share_global_limit():
    """Two back-to-back requests from *different* users still hit the
    global 25 req/s gate (40 ms window), so the second is rejected."""
    assert await rl.check_rate_limit(1) is True
    # No sleep → global interval not elapsed → second user should be denied
    assert await rl.check_rate_limit(2) is False


@pytest.mark.asyncio
async def test_request_allowed_after_global_cooldown():
    assert await rl.check_rate_limit(1) is True
    await asyncio.sleep(0.06)  # > 40 ms global interval
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
async def test_global_last_timestamp_updated_on_allow():
    await rl.check_rate_limit(1)
    assert rl._global_last > 0.0


@pytest.mark.asyncio
async def test_returns_bool():
    result = await rl.check_rate_limit(5)
    assert isinstance(result, bool)
