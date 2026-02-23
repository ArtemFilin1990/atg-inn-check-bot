from __future__ import annotations

import logging
from typing import Any

import asyncpg

from app.config import config

logger = logging.getLogger(__name__)


def postgres_enabled() -> bool:
    values = [
        config.POSTGRES_HOST,
        config.POSTGRES_DB,
        config.POSTGRES_USER,
        config.POSTGRES_PASSWORD,
    ]
    return all(values)


async def create_pool() -> asyncpg.Pool[Any]:
    return await asyncpg.create_pool(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=config.POSTGRES_DB,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        min_size=1,
        max_size=5,
    )


async def init_db(pool: asyncpg.Pool[Any]) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS check_requests (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )


async def log_request(pool: asyncpg.Pool[Any], query: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO check_requests (query) VALUES ($1)", query)

