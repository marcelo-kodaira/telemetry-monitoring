import asyncpg

from app.core.domain import VehicleStatus
from app.features.vehicles.schemas import StatusResult

# Lock the vehicle row and return its current status in one statement. DO UPDATE (even a no-op)
# takes the same exclusive row lock as SELECT ... FOR UPDATE, so concurrent faults still serialize;
# the INSERT branch self-heals an unseeded id.
_LOCK_VEHICLE = """
INSERT INTO vehicles (id, status) VALUES ($1, $2)
ON CONFLICT (id) DO UPDATE SET id = vehicles.id
RETURNING status
"""


async def apply_fault(conn: asyncpg.Connection, vehicle_id: str, reason: str | None) -> StatusResult:
    status = await conn.fetchval(_LOCK_VEHICLE, vehicle_id, VehicleStatus.IDLE)

    if status == VehicleStatus.FAULT:  # idempotent: already faulted, do not duplicate
        existing = await conn.fetchval(
            "SELECT id FROM maintenance WHERE vehicle_id = $1 AND status = 'open'", vehicle_id
        )
        return StatusResult(
            vehicle_id=vehicle_id, status=VehicleStatus.FAULT, fault_handled=False,
            maintenance_id=existing, mission_cancelled=False,
        )

    await conn.execute("UPDATE vehicles SET status = 'fault' WHERE id = $1", vehicle_id)
    cancelled_mission = await conn.fetchval(
        "UPDATE missions SET status = 'cancelled' WHERE vehicle_id = $1 AND status = 'active' RETURNING id",
        vehicle_id,
    )
    maintenance_id = await conn.fetchval(
        "INSERT INTO maintenance (vehicle_id, reason, status) VALUES ($1, $2, 'open')"
        " ON CONFLICT (vehicle_id) WHERE status = 'open' DO NOTHING RETURNING id",
        vehicle_id, reason,
    )
    if maintenance_id is None:  # a stale open record already exists — keep exactly one
        maintenance_id = await conn.fetchval(
            "SELECT id FROM maintenance WHERE vehicle_id = $1 AND status = 'open'", vehicle_id
        )
    return StatusResult(
        vehicle_id=vehicle_id, status=VehicleStatus.FAULT, fault_handled=True,
        maintenance_id=maintenance_id, mission_cancelled=cancelled_mission is not None,
    )


async def apply_status(
    conn: asyncpg.Connection, vehicle_id: str, status: VehicleStatus, reason: str | None
) -> StatusResult:
    if status == VehicleStatus.FAULT:
        return await apply_fault(conn, vehicle_id, reason)
    await conn.execute("UPDATE vehicles SET status = $2 WHERE id = $1", vehicle_id, status)
    return StatusResult(vehicle_id=vehicle_id, status=status)
