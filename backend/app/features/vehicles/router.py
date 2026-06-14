from fastapi import APIRouter, HTTPException

from app.core.db import get_pool, transaction
from app.features.vehicles.list_vehicles import list_vehicles
from app.features.vehicles.schemas import StatusResult, StatusUpdate, VehicleView
from app.features.vehicles.status_update import apply_status

router = APIRouter(tags=["vehicles"])


@router.post("/vehicles/{vehicle_id}/status", response_model=StatusResult, summary="Update vehicle status")
async def post_status(vehicle_id: str, body: StatusUpdate) -> StatusResult:
    exists = await get_pool().fetchval("SELECT 1 FROM vehicles WHERE id = $1", vehicle_id)
    if not exists:
        raise HTTPException(status_code=404, detail=f"unknown vehicle {vehicle_id}")
    async with transaction() as conn:
        return await apply_status(conn, vehicle_id, body.status, body.reason)


@router.get("/vehicles", response_model=list[VehicleView], summary="List all vehicles with latest anomaly")
async def get_vehicles() -> list[dict]:
    async with get_pool().acquire() as conn:
        return await list_vehicles(conn)
