import logging
import os
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get('REF_DB_PATH', 'db/reference_data.sqlite')

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS okved (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS regions (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
"""


class ReferenceData:
    def __init__(self, db_path: str = _DB_PATH):
        self._path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        for stmt in _CREATE_SQL.strip().split(';'):
            stmt = stmt.strip()
            if stmt:
                await self._db.execute(stmt)
        await self._db.commit()
        logger.info("Reference DB ready at %s", self._path)

    async def close(self):
        if self._db:
            await self._db.close()

    async def get_okved_name(self, code: str) -> Optional[str]:
        if not self._db or not code:
            return None
        async with self._db.execute('SELECT name FROM okved WHERE code=?', (code,)) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def get_region_name(self, code: str) -> Optional[str]:
        if not self._db or not code:
            return None
        async with self._db.execute('SELECT name FROM regions WHERE code=?', (code,)) as cur:
            row = await cur.fetchone()
        return row[0] if row else None
