import asyncpg

from app.features.vehicles.schemas import LatestAnomaly, VehicleView

_SQL = """
SELECT v.id AS vehicle_id, v.status, v.battery_pct, v.lat, v.lon, v.is_offline, v.last_seen_at,
       a.type AS a_type, a.severity AS a_severity, a.detected_at AS a_detected_at
FROM vehicles v
LEFT JOIN LATERAL (
    SELECT type, severity, detected_at FROM anomalies
    WHERE vehicle_id = v.id ORDER BY detected_at DESC LIMIT 1
) a ON true
ORDER BY v.id
"""


async def list_vehicles(conn: asyncpg.Connection) -> list[VehicleView]:
    rows = await conn.fetch(_SQL)
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
