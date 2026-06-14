from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg

from app.core.config import settings

_pool: asyncpg.Pool | None = None
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"


async def init_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
    )
    return _pool


async def apply_schema() -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(SCHEMA_PATH.read_text())


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("pool not initialized")
    return _pool


@asynccontextmanager
async def transaction():
    async with get_pool().acquire() as conn:
        async with conn.transaction():
            yield conn
