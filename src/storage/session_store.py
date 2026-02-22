import json
import logging
import os
import time
from typing import Any, Dict, Optional

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get('SESSION_DB_PATH',
                           os.path.join(os.environ.get('DB_DIR', '/data/db'), 'sessions.sqlite'))

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    user_id INTEGER PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""
_SESSION_TTL = 7 * 24 * 3600  # 7 days


class SessionStore:
    def __init__(self, db_path: str = _DB_PATH):
        self._path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute(_CREATE_SQL)
        await self._db.commit()
        logger.info("Session store ready at %s", self._path)

    async def close(self):
        if self._db:
            await self._db.close()

    async def get(self, user_id: int) -> Dict[str, Any]:
        if not self._db:
            return {}
        async with self._db.execute(
            'SELECT data, updated_at FROM sessions WHERE user_id=?', (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return {}
        data_json, updated_at = row
        if time.time() - updated_at > _SESSION_TTL:
            await self._db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
            await self._db.commit()
            return {}
        return json.loads(data_json)

    async def set(self, user_id: int, data: Dict[str, Any]):
        if not self._db:
            return
        await self._db.execute(
            'INSERT OR REPLACE INTO sessions (user_id, data, updated_at) VALUES (?, ?, ?)',
            (user_id, json.dumps(data, ensure_ascii=False, default=str), time.time()),
        )
        await self._db.commit()

    async def set_field(self, user_id: int, key: str, value: Any):
        data = await self.get(user_id)
        data[key] = value
        await self.set(user_id, data)

    async def get_field(self, user_id: int, key: str, default=None) -> Any:
        data = await self.get(user_id)
        return data.get(key, default)

    async def cleanup(self):
        if not self._db:
            return
        cutoff = time.time() - _SESSION_TTL
        await self._db.execute('DELETE FROM sessions WHERE updated_at < ?', (cutoff,))
        await self._db.commit()
