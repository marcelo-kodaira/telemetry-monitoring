import asyncpg

from app.core.domain import VehicleStatus
from app.features.telemetry.anomaly_rules import Anomaly, evaluate
from app.features.telemetry.schemas import DetectedAnomaly, IngestResult, TelemetryEvent
from app.features.vehicles import apply_fault

# Vehicle snapshot columns in one place — the FOR UPDATE read and the upsert below share this order.
_SNAPSHOT_COLS = "status, battery_pct, lat, lon, speed_mps, last_timestamp, active_anomaly_types"

_LOCK_PREVIOUS = f"SELECT {_SNAPSHOT_COLS} FROM vehicles WHERE id = $1 FOR UPDATE"

_INSERT_TELEMETRY = """
INSERT INTO telemetry
    (vehicle_id, ts, lat, lon, battery_pct, speed_mps, status, error_codes, zone_entered)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
"""

_INSERT_ANOMALY = "INSERT INTO anomalies (vehicle_id, type, severity, details) VALUES ($1, $2, $3, $4)"

_BUMP_ZONE_COUNTER = "UPDATE zone_counts SET entry_count = entry_count + 1 WHERE zone_id = $1"

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
    conn: asyncpg.Connection, vehicle_id: str, previous_types: set[str], active_anomalies: list[Anomaly]
) -> list[Anomaly]:
    """Edge-triggered: persist only anomaly types that were not already active for this vehicle."""
    new_anomalies = [anomaly for anomaly in active_anomalies if anomaly.type not in previous_types]
    for anomaly in new_anomalies:
        await conn.execute(_INSERT_ANOMALY, vehicle_id, anomaly.type, anomaly.severity, anomaly.details)
    return new_anomalies


async def ingest_event(conn: asyncpg.Connection, event: TelemetryEvent) -> IngestResult:
    # Lock the vehicle row (if seeded) to serialize same-vehicle events for stateful diffing.
    previous_row = await conn.fetchrow(_LOCK_PREVIOUS, event.vehicle_id)
    previous = dict(previous_row) if previous_row else None

    await conn.execute(
        _INSERT_TELEMETRY,
        event.vehicle_id, event.ts, event.lat, event.lon, event.battery_pct, event.speed_mps,
        event.status, event.error_codes, event.zone_entered,
    )

    active_anomalies = evaluate(previous, event)
    previous_types = set(previous["active_anomaly_types"]) if previous else set()
    new_anomalies = await _persist_new_anomalies(conn, event.vehicle_id, previous_types, active_anomalies)

    if event.zone_entered is not None:
        await conn.execute(_BUMP_ZONE_COUNTER, event.zone_entered)

    await conn.execute(
        _UPSERT_SNAPSHOT,
        event.vehicle_id, event.status, event.battery_pct, event.lat, event.lon, event.speed_mps,
        event.ts, [anomaly.type for anomaly in active_anomalies],
    )

    if event.status == VehicleStatus.FAULT:
        await apply_fault(conn, event.vehicle_id, reason="fault reported via telemetry")

    return IngestResult(
        detected_anomalies=[DetectedAnomaly(type=a.type, severity=a.severity) for a in new_anomalies]
    )
