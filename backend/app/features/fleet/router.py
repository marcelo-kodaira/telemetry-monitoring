from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.db import get_pool

router = APIRouter(tags=["fleet"])


@router.get("/fleet/state", summary="Aggregate per-status counts (MVCC-safe)")
async def get_fleet_state():
    pool = get_pool()
    rows = await pool.fetch("SELECT status, count(*) AS n FROM vehicles GROUP BY status")
    offline = await pool.fetchval("SELECT count(*) FROM vehicles WHERE is_offline")
    total = await pool.fetchval("SELECT count(*) FROM vehicles")
    counts = {"idle": 0, "moving": 0, "charging": 0, "fault": 0}
    for r in rows:
        counts[r["status"]] = r["n"]
    return {
        "generated_at": datetime.now(timezone.utc),
        "total": total,
        "offline": offline,
        "counts": counts,
    }
