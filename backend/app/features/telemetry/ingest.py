import asyncpg

from app.core.domain import VehicleStatus
from app.features.telemetry.anomaly_rules import Anomaly, evaluate
from app.features.telemetry.schemas import DetectedAnomaly, IngestResult, TelemetryEvent
from app.features.vehicles.status_update import apply_fault

# Vehicle snapshot columns in one place — the FOR UPDATE read and the upsert below share this order.
_SNAPSHOT_COLS = "status, battery_pct, lat, lon, speed_mps, last_timestamp, active_anomaly_types"

_LOCK_PREV = f"SELECT {_SNAPSHOT_COLS} FROM vehicles WHERE id = $1 FOR UPDATE"

_INSERT_TELEMETRY = """
INSERT INTO telemetry
    (vehicle_id, ts, lat, lon, battery_pct, speed_mps, status, error_codes, zone_entered)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
"""

_INSERT_ANOMALY = "INSERT INTO anomalies (vehicle_id, type, severity, details) VALUES ($1, $2, $3, $4)"

_BUMP_ZONE = "UPDATE zone_counts SET entry_count = entry_count + 1 WHERE zone_id = $1"

_UPSERT_SNAPSHOT = """
INSERT INTO vehicles
    (id, status, battery_pct, lat, lon, speed_mps, last_timestamp, last_seen_at, is_offline, active_anomaly_types)
VALUES ($1, $2, $3, $4, $5, $6, $7, now(), false, $8)
ON CONFLICT (id) DO UPDATE SET
    -- fault is terminal until maintenance is resolved: non-fault telemetry must not clear it
    status = CASE WHEN vehicles.status = 'fault' THEN 'fault' ELSE excluded.status END,
    battery_pct = excluded.battery_pct,
    lat = excluded.lat,
    lon = excluded.lon,
    speed_mps = excluded.speed_mps,
    last_timestamp = excluded.last_timestamp,
    last_seen_at = now(),
    is_offline = false,
    active_anomaly_types = excluded.active_anomaly_types
WHERE excluded.last_timestamp > vehicles.last_timestamp OR vehicles.last_timestamp IS NULL
"""


async def _persist_new_anomalies(
    conn: asyncpg.Connection, vehicle_id: str, prev_types: set[str], active: list[Anomaly]
) -> list[Anomaly]:
    """Edge-triggered: persist only anomaly types that were not already active for this vehicle."""
    new = [a for a in active if a.type not in prev_types]
    for a in new:
        await conn.execute(_INSERT_ANOMALY, vehicle_id, a.type, a.severity, a.details)
    return new


async def ingest_event(conn: asyncpg.Connection, e: TelemetryEvent) -> IngestResult:
    # Lock the vehicle row (if seeded) to serialize same-vehicle events for stateful diffing.
    prev = await conn.fetchrow(_LOCK_PREV, e.vehicle_id)
    prev_dict = dict(prev) if prev else None

    await conn.execute(
        _INSERT_TELEMETRY,
        e.vehicle_id, e.ts, e.lat, e.lon, e.battery_pct, e.speed_mps, e.status, e.error_codes, e.zone_entered,
    )

    active = evaluate(prev_dict, e)
    prev_types = set(prev_dict["active_anomaly_types"]) if prev_dict else set()
    new = await _persist_new_anomalies(conn, e.vehicle_id, prev_types, active)

    if e.zone_entered is not None:
        await conn.execute(_BUMP_ZONE, e.zone_entered)

    await conn.execute(
        _UPSERT_SNAPSHOT,
        e.vehicle_id, e.status, e.battery_pct, e.lat, e.lon, e.speed_mps, e.ts,
        [a.type for a in active],
    )

    if e.status == VehicleStatus.FAULT:
        await apply_fault(conn, e.vehicle_id, reason="fault reported via telemetry")

    return IngestResult(
        detected_anomalies=[DetectedAnomaly(type=a.type, severity=a.severity) for a in new]
    )
