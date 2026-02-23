import time
import asyncio
from collections import deque


class RateLimiter:
    """Sliding-window rate limiter: max `rate` calls per second globally."""

    def __init__(self, rate: int = 25) -> None:
        self._rate = rate
        self._timestamps: deque = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            # drop timestamps older than 1 second
            while self._timestamps and now - self._timestamps[0] >= 1.0:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._rate:
                sleep_for = 1.0 - (now - self._timestamps[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                # re-clean after sleeping
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= 1.0:
                    self._timestamps.popleft()
            self._timestamps.append(time.monotonic())
