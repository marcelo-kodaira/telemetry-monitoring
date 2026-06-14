import asyncpg

from app.features.vehicles.schemas import StatusResult


async def apply_fault(conn: asyncpg.Connection, vehicle_id: str, reason: str | None) -> StatusResult:
    row = await conn.fetchrow("SELECT status FROM vehicles WHERE id = $1 FOR UPDATE", vehicle_id)
    if row is None:
        await conn.execute(
            "INSERT INTO vehicles (id, status) VALUES ($1, 'idle') ON CONFLICT (id) DO NOTHING",
            vehicle_id,
        )
        row = await conn.fetchrow("SELECT status FROM vehicles WHERE id = $1 FOR UPDATE", vehicle_id)

    if row["status"] == "fault":  # idempotent: already faulted, do not duplicate
        existing = await conn.fetchval(
            "SELECT id FROM maintenance WHERE vehicle_id = $1 AND status = 'open'", vehicle_id
        )
        return StatusResult(
            vehicle_id=vehicle_id, status="fault", fault_handled=False,
            maintenance_id=existing, mission_cancelled=False,
        )

    await conn.execute("UPDATE vehicles SET status = 'fault' WHERE id = $1", vehicle_id)
    cancelled_tag = await conn.execute(
        "UPDATE missions SET status = 'cancelled' WHERE vehicle_id = $1 AND status = 'active'",
        vehicle_id,
    )
    maintenance_id = await conn.fetchval(
        "INSERT INTO maintenance (vehicle_id, reason, status) VALUES ($1, $2, 'open')"
        " ON CONFLICT (vehicle_id) WHERE status = 'open' DO NOTHING RETURNING id",
        vehicle_id, reason,
    )
    if maintenance_id is None:  # an open record already exists — keep exactly one
        maintenance_id = await conn.fetchval(
            "SELECT id FROM maintenance WHERE vehicle_id = $1 AND status = 'open'", vehicle_id
        )
    return StatusResult(
        vehicle_id=vehicle_id, status="fault", fault_handled=True,
        maintenance_id=maintenance_id, mission_cancelled=cancelled_tag.endswith(" 1"),
    )


async def apply_status(
    conn: asyncpg.Connection, vehicle_id: str, status: str, reason: str | None
) -> StatusResult:
    if status == "fault":
        return await apply_fault(conn, vehicle_id, reason)
    await conn.execute("UPDATE vehicles SET status = $2 WHERE id = $1", vehicle_id, status)
    return StatusResult(vehicle_id=vehicle_id, status=status)
