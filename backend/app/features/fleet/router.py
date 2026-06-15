from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.db import get_pool
from app.core.domain import VehicleStatus

router = APIRouter(tags=["fleet"])


@router.get("/fleet/state", summary="Aggregate per-status counts (MVCC-safe)")
async def get_fleet_state():
    pool = get_pool()
    rows = await pool.fetch("SELECT status, count(*) AS n FROM vehicles GROUP BY status")
    offline = await pool.fetchval("SELECT count(*) FROM vehicles WHERE is_offline")
    total = await pool.fetchval("SELECT count(*) FROM vehicles")
    counts = {s.value: 0 for s in VehicleStatus}
    for r in rows:
        counts[r["status"]] = r["n"]
    return {
        "generated_at": datetime.now(timezone.utc),
        "total": total,
        "offline": offline,
        "counts": counts,
    }
