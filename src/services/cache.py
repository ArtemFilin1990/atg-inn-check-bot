import json
import logging
import os
import time
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get('CACHE_DB_PATH', '/data/db/cache.sqlite')

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at REAL NOT NULL
);
"""


class SQLiteCache:
    def __init__(self, db_path: str = _DB_PATH):
        self._path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute(_CREATE_SQL)
        await self._db.commit()
        logger.info("Cache DB ready at %s", self._path)

    async def close(self):
        if self._db:
            await self._db.close()

    async def get(self, key: str) -> Optional[Any]:
        if not self._db:
            return None
        async with self._db.execute(
            'SELECT value, expires_at FROM cache WHERE key=?', (key,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        value_json, expires_at = row
        if time.time() > expires_at:
            await self._db.execute('DELETE FROM cache WHERE key=?', (key,))
            await self._db.commit()
            return None
        return json.loads(value_json)

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        if not self._db:
            return
        expires_at = time.time() + ttl_seconds
        await self._db.execute(
            'INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)',
            (key, json.dumps(value, ensure_ascii=False, default=str), expires_at),
        )
        await self._db.commit()

    async def cleanup(self):
        """Remove expired entries."""
        if not self._db:
            return
        await self._db.execute('DELETE FROM cache WHERE expires_at < ?', (time.time(),))
        await self._db.commit()
