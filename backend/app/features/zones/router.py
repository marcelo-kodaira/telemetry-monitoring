from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.db import get_pool

router = APIRouter(tags=["zones"])


@router.get("/zones/counts", summary="Per-zone entry counts")
async def get_zone_counts():
    rows = await get_pool().fetch("SELECT zone_id, entry_count FROM zone_counts ORDER BY zone_id")
    return {
        "generated_at": datetime.now(timezone.utc),
        "zones": [{"zone_id": r["zone_id"], "entry_count": r["entry_count"]} for r in rows],
    }
