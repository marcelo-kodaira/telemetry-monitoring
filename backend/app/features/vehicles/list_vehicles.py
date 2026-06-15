import asyncpg

from app.features.vehicles import queries
from app.features.vehicles.schemas import LatestAnomaly, VehicleView


async def list_vehicles(conn: asyncpg.Connection) -> list[VehicleView]:
    rows = await conn.fetch(queries.LIST_WITH_LATEST_ANOMALY)
    vehicles: list[VehicleView] = []
    for row in rows:
        latest_anomaly = None
        if row["a_type"] is not None:
            latest_anomaly = LatestAnomaly(
                type=row["a_type"], severity=row["a_severity"], detected_at=row["a_detected_at"]
            )
        vehicles.append(
            VehicleView(
                vehicle_id=row["vehicle_id"], status=row["status"], battery_pct=row["battery_pct"],
                lat=row["lat"], lon=row["lon"], is_offline=row["is_offline"],
                last_seen_at=row["last_seen_at"], latest_anomaly=latest_anomaly,
            )
        )
    return vehicles
