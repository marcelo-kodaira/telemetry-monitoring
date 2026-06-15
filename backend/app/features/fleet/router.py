from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.db import get_pool
from app.core.domain import VehicleStatus

router = APIRouter(tags=["fleet"])


class FleetStateView(BaseModel):
    generated_at: datetime
    total: int
    offline: int
    counts: dict[str, int]


@router.get("/fleet/state", summary="Aggregate per-status counts (MVCC-safe)")
async def get_fleet_state() -> FleetStateView:
    pool = get_pool()
    rows = await pool.fetch("SELECT status, count(*) AS n FROM vehicles GROUP BY status")
    offline = await pool.fetchval("SELECT count(*) FROM vehicles WHERE is_offline")
    total = await pool.fetchval("SELECT count(*) FROM vehicles")
    counts = {status.value: 0 for status in VehicleStatus}
    for row in rows:
        counts[row["status"]] = row["n"]
    return FleetStateView(
        generated_at=datetime.now(timezone.utc), total=total, offline=offline, counts=counts
    )
