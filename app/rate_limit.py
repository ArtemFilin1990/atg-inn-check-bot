import time
import asyncio
from collections import defaultdict

# Per-user: max 1 request per 0.5 seconds
_user_last: dict[int, float] = defaultdict(float)
_user_lock = asyncio.Lock()


async def check_rate_limit(user_id: int) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.monotonic()

    async with _user_lock:
        user_elapsed = now - _user_last[user_id]
        if user_elapsed < 0.5:
            return False
        _user_last[user_id] = now

    return True
