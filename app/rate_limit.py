import time
import asyncio
from collections import defaultdict

# Per-user: max 1 request per 0.5 seconds
_user_last: dict[int, float] = defaultdict(float)
_user_lock = asyncio.Lock()

# Global: max 25 req/sec using token-bucket-like approach
_global_last: float = 0.0
_global_lock = asyncio.Lock()
_MIN_INTERVAL = 1.0 / 25  # 40 ms


async def check_rate_limit(user_id: int) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.monotonic()

    async with _global_lock:
        elapsed = now - _global_last
        if elapsed < _MIN_INTERVAL:
            return False
        global _global_last
        _global_last = now

    async with _user_lock:
        user_elapsed = now - _user_last[user_id]
        if user_elapsed < 0.5:
            return False
        _user_last[user_id] = now

    return True
