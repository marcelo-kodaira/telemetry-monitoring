from datetime import datetime

from fastapi import APIRouter, Query

from app.core.db import get_pool
from app.features.anomalies.schemas import AnomalyListView, AnomalyView

router = APIRouter(tags=["anomalies"])


@router.get("/anomalies", summary="Query recent anomalies by vehicle and time range")
async def get_anomalies(
    vehicle_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> AnomalyListView:
    clauses: list[str] = []
    args: list = []
    if vehicle_id is not None:
        args.append(vehicle_id)
        clauses.append(f"vehicle_id = ${len(args)}")
    if start is not None:
        args.append(start)
        clauses.append(f"detected_at >= ${len(args)}")
    if end is not None:
        args.append(end)
        clauses.append(f"detected_at < ${len(args)}")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    args.append(limit)

    rows = await get_pool().fetch(
        f"SELECT id, vehicle_id, type, severity, detected_at, details FROM anomalies"
        f"{where} ORDER BY detected_at DESC LIMIT ${len(args)}",
        *args,
    )
    items = [
        AnomalyView(
            id=r["id"], vehicle_id=r["vehicle_id"], type=r["type"], severity=r["severity"],
            detected_at=r["detected_at"], details=r["details"],
        )
        for r in rows
    ]
    return AnomalyListView(count=len(items), anomalies=items)
