from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.db import get_pool
from app.core.domain import VehicleStatus
from app.features.fleet import queries

router = APIRouter(tags=["fleet"])


class FleetStateView(BaseModel):
    generated_at: datetime
    total: int
    offline: int
    counts: dict[str, int]


@router.get("/fleet/state", summary="Aggregate per-status counts (MVCC-safe)")
async def get_fleet_state() -> FleetStateView:
    pool = get_pool()
    rows = await pool.fetch(queries.STATUS_COUNTS)
    offline = await pool.fetchval(queries.OFFLINE_COUNT)
    total = await pool.fetchval(queries.TOTAL_COUNT)
    counts = {status.value: 0 for status in VehicleStatus}
    for row in rows:
        counts[row["status"]] = row["n"]
    return FleetStateView(
        generated_at=datetime.now(timezone.utc), total=total, offline=offline, counts=counts
    )
