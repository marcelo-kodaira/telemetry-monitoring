import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core import db as db_mod
from app.main import app


@pytest_asyncio.fixture
async def pool():
    p = await db_mod.init_pool()  # same pool setup as prod (incl. the jsonb codec)
    await db_mod.apply_schema()
    yield p
    await db_mod.close_pool()


@pytest_asyncio.fixture
async def reset_db(pool):
    async with pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE telemetry, anomalies, maintenance RESTART IDENTITY;"
            "UPDATE zone_counts SET entry_count = 0;"
            "UPDATE vehicles SET status='idle', battery_pct=100, speed_mps=0, lat=NULL, lon=NULL,"
            " last_timestamp=NULL, is_offline=false, active_anomaly_types='{}';"
            "DELETE FROM missions;"
            "INSERT INTO missions (vehicle_id, status) SELECT 'v-'||g,'active' FROM generate_series(1,50) g;"
        )
    yield


@pytest_asyncio.fixture
async def client(pool, reset_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
