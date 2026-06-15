from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.db import get_pool
from app.features.zones import queries

router = APIRouter(tags=["zones"])


class ZoneCount(BaseModel):
    zone_id: str
    entry_count: int


class ZoneCountsView(BaseModel):
    generated_at: datetime
    zones: list[ZoneCount]


@router.get("/zones/counts", summary="Per-zone entry counts")
async def get_zone_counts() -> ZoneCountsView:
    rows = await get_pool().fetch(queries.ZONE_COUNTS)
    return ZoneCountsView(
        generated_at=datetime.now(timezone.utc),
        zones=[ZoneCount(zone_id=row["zone_id"], entry_count=row["entry_count"]) for row in rows],
    )
