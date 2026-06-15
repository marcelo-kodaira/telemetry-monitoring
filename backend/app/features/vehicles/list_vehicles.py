import asyncpg

from app.features.vehicles import queries
from app.features.vehicles.schemas import VehicleView


async def list_vehicles(conn: asyncpg.Connection) -> list[VehicleView]:
    rows = await conn.fetch(queries.LIST_VEHICLES)
    return [
        VehicleView(
            vehicle_id=row["vehicle_id"], status=row["status"], battery_pct=row["battery_pct"],
            lat=row["lat"], lon=row["lon"], is_offline=row["is_offline"],
            last_seen_at=row["last_seen_at"], active_anomalies=list(row["active_anomaly_types"]),
        )
        for row in rows
    ]
