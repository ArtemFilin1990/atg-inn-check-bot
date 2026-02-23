from __future__ import annotations

import pytest

from app import db


class DummyConn:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *params: object) -> None:
        self.executed.append((query, params))


class DummyAcquire:
    def __init__(self, conn: DummyConn) -> None:
        self.conn = conn

    async def __aenter__(self) -> DummyConn:
        return self.conn

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class DummyPool:
    def __init__(self, conn: DummyConn) -> None:
        self.conn = conn

    def acquire(self) -> DummyAcquire:
        return DummyAcquire(self.conn)


@pytest.mark.asyncio
async def test_init_db_executes_create_table() -> None:
    conn = DummyConn()
    pool = DummyPool(conn)

    await db.init_db(pool)

    assert conn.executed
    assert "CREATE TABLE IF NOT EXISTS check_requests" in conn.executed[0][0]


@pytest.mark.asyncio
async def test_log_request_executes_insert() -> None:
    conn = DummyConn()
    pool = DummyPool(conn)

    await db.log_request(pool, "7707083893")

    assert conn.executed == [
        ("INSERT INTO check_requests (query) VALUES ($1)", ("7707083893",)),
    ]


def test_postgres_enabled_uses_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db.config, "POSTGRES_HOST", "db")
    monkeypatch.setattr(db.config, "POSTGRES_DB", "bearing")
    monkeypatch.setattr(db.config, "POSTGRES_USER", "user")
    monkeypatch.setattr(db.config, "POSTGRES_PASSWORD", "secret")

    assert db.postgres_enabled() is True

    monkeypatch.setattr(db.config, "POSTGRES_PASSWORD", None)
    assert db.postgres_enabled() is False
