import asyncio
import logging

from app.core.config import settings
from app.core.db import get_pool
from app.features.anomalies import queries

logger = logging.getLogger(__name__)


async def sweep_once() -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(queries.MARK_NEWLY_OFFLINE, str(settings.staleness_seconds))


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
