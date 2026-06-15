import asyncio
import logging

from app.core.config import settings
from app.core.db import get_pool
from app.core.domain import AnomalyType, Severity

logger = logging.getLogger(__name__)

_STMT = f"""
WITH newly_offline AS (
    UPDATE vehicles SET is_offline = true
    WHERE NOT is_offline AND last_seen_at < now() - ($1 || ' seconds')::interval
    RETURNING id
)
INSERT INTO anomalies (vehicle_id, type, severity, details)
SELECT id, '{AnomalyType.STALE_OFFLINE}', '{Severity.CRITICAL}', '{{}}'::jsonb FROM newly_offline
"""


async def sweep_once() -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(_STMT, str(settings.staleness_seconds))


async def _loop() -> None:
    while True:
        await asyncio.sleep(settings.sweep_interval_seconds)
        try:
            await sweep_once()
        except Exception:  # resilient loop, but a recurring failure must be visible
            logger.exception("staleness sweep failed")


def start_staleness_sweep() -> asyncio.Task:
    return asyncio.create_task(_loop())


async def stop_staleness_sweep(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
