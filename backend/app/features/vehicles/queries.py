"""SQL for the vehicles slice. Statements only — the handlers own the connection and transaction."""

# Lock the vehicle row and return its current status in one statement. DO UPDATE (even a no-op) takes
# the same exclusive row lock as SELECT ... FOR UPDATE, so concurrent faults still serialize; the
# INSERT branch self-heals an unseeded id.
LOCK_VEHICLE = """
INSERT INTO vehicles (id, status) VALUES ($1, $2)
ON CONFLICT (id) DO UPDATE SET id = vehicles.id
RETURNING status
"""

SET_FAULT = "UPDATE vehicles SET status = 'fault' WHERE id = $1"

CANCEL_ACTIVE_MISSION = (
    "UPDATE missions SET status = 'cancelled' WHERE vehicle_id = $1 AND status = 'active' RETURNING id"
)

OPEN_MAINTENANCE = """
INSERT INTO maintenance (vehicle_id, reason, status) VALUES ($1, $2, 'open')
ON CONFLICT (vehicle_id) WHERE status = 'open' DO NOTHING
RETURNING id
"""

EXISTING_OPEN_MAINTENANCE_ID = "SELECT id FROM maintenance WHERE vehicle_id = $1 AND status = 'open'"

SET_STATUS = "UPDATE vehicles SET status = $2 WHERE id = $1"

VEHICLE_EXISTS = "SELECT 1 FROM vehicles WHERE id = $1"

LIST_WITH_LATEST_ANOMALY = """
SELECT v.id AS vehicle_id, v.status, v.battery_pct, v.lat, v.lon, v.is_offline, v.last_seen_at,
       a.type AS a_type, a.severity AS a_severity, a.detected_at AS a_detected_at
FROM vehicles v
LEFT JOIN LATERAL (
    SELECT type, severity, detected_at FROM anomalies
    WHERE vehicle_id = v.id ORDER BY detected_at DESC LIMIT 1
) a ON true
ORDER BY v.id
"""
