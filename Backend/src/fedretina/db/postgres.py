"""Async PostgreSQL connection pool.

We use asyncpg directly (not SQLAlchemy) because:

1. It is the fastest async Postgres driver for Python.
2. Our queries are simple enough that an ORM adds friction, not leverage.
3. It exposes the exact semantics we need for the audit chain (transactions,
   advisory locks, prepared statements) without translation layers.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Final

import asyncpg

from fedretina.config import get_settings
from fedretina.logging import get_logger

log = get_logger("db.postgres")

_pool: asyncpg.Pool | None = None
_pool_lock: Final = asyncio.Lock()


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Per-connection setup hook: register JSON/JSONB codecs."""
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def init_pool() -> asyncpg.Pool:
    """Create the global connection pool. Idempotent."""
    global _pool

    async with _pool_lock:
        if _pool is not None:
            return _pool

        settings = get_settings()
        dsn = settings.database_url.get_secret_value()

        log.info("db.pool.init.begin")

        try:
            _pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=10,
                max_inactive_connection_lifetime=300.0,
                command_timeout=settings.request_timeout_seconds,
                statement_cache_size=0,
                init=_init_connection,
            )
        except Exception:
            log.exception("db.pool.init.failed")
            raise

        log.info("db.pool.init.ready")
        return _pool


async def close_pool() -> None:
    """Close the global pool. Idempotent."""
    global _pool

    async with _pool_lock:
        if _pool is None:
            return
        log.info("db.pool.close.begin")
        await _pool.close()
        _pool = None
        log.info("db.pool.close.complete")


def get_pool() -> asyncpg.Pool:
    """Return the pool. Raises if called before init_pool()."""
    if _pool is None:
        raise RuntimeError(
            "Connection pool is not initialized. "
            "Ensure init_pool() ran during application startup."
        )
    return _pool


async def ping() -> bool:
    """Return True if the DB answers SELECT 1. Never raises."""
    if _pool is None:
        return False
    try:
        async with _pool.acquire() as conn:
            result: Any = await conn.fetchval("SELECT 1")
        return result == 1
    except Exception:
        log.exception("db.ping.failed")
        return False
