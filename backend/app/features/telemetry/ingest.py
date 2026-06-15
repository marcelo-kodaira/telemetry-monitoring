import asyncpg

from app.core.domain import VehicleStatus
from app.features.telemetry import queries
from app.features.telemetry.anomaly_rules import Anomaly, evaluate
from app.features.telemetry.schemas import DetectedAnomaly, IngestResult, TelemetryEvent
from app.features.vehicles import apply_fault


async def _persist_new_anomalies(
    conn: asyncpg.Connection, vehicle_id: str, previous_types: set[str], active_anomalies: list[Anomaly]
) -> list[Anomaly]:
    """Edge-triggered: persist only anomaly types that were not already active for this vehicle."""
    new_anomalies = [anomaly for anomaly in active_anomalies if anomaly.type not in previous_types]
    for anomaly in new_anomalies:
        await conn.execute(queries.INSERT_ANOMALY, vehicle_id, anomaly.type, anomaly.severity, anomaly.details)
    return new_anomalies


async def ingest_event(conn: asyncpg.Connection, event: TelemetryEvent) -> IngestResult:
    # Lock the vehicle row (if seeded) to serialize same-vehicle events for stateful diffing.
    previous_row = await conn.fetchrow(queries.LOCK_PREVIOUS, event.vehicle_id)
    previous = dict(previous_row) if previous_row else None

    await conn.execute(
        queries.INSERT_TELEMETRY,
        event.vehicle_id, event.ts, event.lat, event.lon, event.battery_pct, event.speed_mps,
        event.status, event.error_codes, event.zone_entered,
    )

    active_anomalies = evaluate(previous, event)
    previous_types = set(previous["active_anomaly_types"]) if previous else set()
    new_anomalies = await _persist_new_anomalies(conn, event.vehicle_id, previous_types, active_anomalies)

    if event.zone_entered is not None:
        await conn.execute(queries.BUMP_ZONE_COUNTER, event.zone_entered)

    await conn.execute(
        queries.UPSERT_SNAPSHOT,
        event.vehicle_id, event.status, event.battery_pct, event.lat, event.lon, event.speed_mps,
        event.ts, [anomaly.type for anomaly in active_anomalies],
    )

    if event.status == VehicleStatus.FAULT:
        await apply_fault(conn, event.vehicle_id, reason="fault reported via telemetry")

    return IngestResult(
        detected_anomalies=[DetectedAnomaly(type=a.type, severity=a.severity) for a in new_anomalies]
    )
