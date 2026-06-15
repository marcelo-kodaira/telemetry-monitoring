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
    out: list[VehicleView] = []
    for r in rows:
        latest = None
        if r["a_type"] is not None:
            latest = LatestAnomaly(type=r["a_type"], severity=r["a_severity"], detected_at=r["a_detected_at"])
        out.append(
            VehicleView(
                vehicle_id=r["vehicle_id"], status=r["status"], battery_pct=r["battery_pct"],
                lat=r["lat"], lon=r["lon"], is_offline=r["is_offline"], last_seen_at=r["last_seen_at"],
                latest_anomaly=latest,
            )
        )
    return out
