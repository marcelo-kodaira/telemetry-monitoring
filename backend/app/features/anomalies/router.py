from datetime import datetime

from fastapi import APIRouter, Query

from app.core.db import get_pool
from app.features.anomalies.schemas import AnomalyListView, AnomalyView

router = APIRouter(tags=["anomalies"])

_SELECT = "SELECT id, vehicle_id, type, severity, detected_at, details FROM anomalies"


@router.get("/anomalies", summary="Query recent anomalies by vehicle and time range")
async def get_anomalies(
    vehicle_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> AnomalyListView:
    args: list = []

    def param(value: object) -> str:  # append a bound value, return its $N placeholder
        args.append(value)
        return f"${len(args)}"

    clauses: list[str] = []
    if vehicle_id is not None:
        clauses.append(f"vehicle_id = {param(vehicle_id)}")
    if start is not None:
        clauses.append(f"detected_at >= {param(start)}")
    if end is not None:
        clauses.append(f"detected_at < {param(end)}")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    rows = await get_pool().fetch(
        f"{_SELECT}{where} ORDER BY detected_at DESC LIMIT {param(limit)}", *args
    )
    items = [
        AnomalyView(
            id=r["id"], vehicle_id=r["vehicle_id"], type=r["type"], severity=r["severity"],
            detected_at=r["detected_at"], details=r["details"],
        )
        for r in rows
    ]
    return AnomalyListView(count=len(items), anomalies=items)
