"""SQL for the telemetry slice. The handler owns the connection/transaction; this module only holds
the statements so the orchestration in ingest.py reads as a sequence of steps, not a wall of SQL."""

# Vehicle snapshot columns in one place — the FOR UPDATE read and the upsert share this order.
SNAPSHOT_COLS = "status, battery_pct, lat, lon, speed_mps, last_timestamp, active_anomaly_types"

LOCK_PREVIOUS = f"SELECT {SNAPSHOT_COLS} FROM vehicles WHERE id = $1 FOR UPDATE"

INSERT_TELEMETRY = """
INSERT INTO telemetry
    (vehicle_id, ts, lat, lon, battery_pct, speed_mps, status, error_codes, zone_entered)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
"""

INSERT_ANOMALY = "INSERT INTO anomalies (vehicle_id, type, severity, details) VALUES ($1, $2, $3, $4)"

BUMP_ZONE_COUNTER = "UPDATE zone_counts SET entry_count = entry_count + 1 WHERE zone_id = $1"

UPSERT_SNAPSHOT = """
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
