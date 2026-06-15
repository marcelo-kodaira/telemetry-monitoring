import asyncpg

from app.core.domain import VehicleStatus
from app.features.vehicles import queries
from app.features.vehicles.schemas import StatusResult


async def apply_fault(conn: asyncpg.Connection, vehicle_id: str, reason: str | None) -> StatusResult:
    status = await conn.fetchval(queries.LOCK_VEHICLE, vehicle_id, VehicleStatus.IDLE)

    if status == VehicleStatus.FAULT:  # idempotent: already faulted, do not duplicate
        existing = await conn.fetchval(queries.EXISTING_OPEN_MAINTENANCE_ID, vehicle_id)
        return StatusResult(
            vehicle_id=vehicle_id, status=VehicleStatus.FAULT, fault_handled=False,
            maintenance_id=existing, mission_cancelled=False,
        )

    await conn.execute(queries.SET_FAULT, vehicle_id)
    cancelled_mission = await conn.fetchval(queries.CANCEL_ACTIVE_MISSION, vehicle_id)
    maintenance_id = await conn.fetchval(queries.OPEN_MAINTENANCE, vehicle_id, reason)
    if maintenance_id is None:  # a stale open record already exists — keep exactly one
        maintenance_id = await conn.fetchval(queries.EXISTING_OPEN_MAINTENANCE_ID, vehicle_id)
    return StatusResult(
        vehicle_id=vehicle_id, status=VehicleStatus.FAULT, fault_handled=True,
        maintenance_id=maintenance_id, mission_cancelled=cancelled_mission is not None,
    )


async def apply_status(
    conn: asyncpg.Connection, vehicle_id: str, status: VehicleStatus, reason: str | None
) -> StatusResult:
    if status == VehicleStatus.FAULT:
        return await apply_fault(conn, vehicle_id, reason)
    await conn.execute(queries.SET_STATUS, vehicle_id, status)
    return StatusResult(vehicle_id=vehicle_id, status=status)
