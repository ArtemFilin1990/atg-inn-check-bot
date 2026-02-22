#!/usr/bin/env python3
"""Build the reference SQLite database from source data.
Run: python tools/build_reference_db.py
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import aiosqlite

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DB_PATH = os.environ.get('REF_DB_PATH', '/data/db/reference_data.sqlite')


async def build():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS okved (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        await db.commit()
        logger.info("Reference DB initialised at %s (populate with real data as needed)", DB_PATH)


if __name__ == '__main__':
    asyncio.run(build())
