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

# active_anomaly_types is the set of conditions active as of the vehicle's latest telemetry — the
# *current* alert state, which clears the moment a condition resolves (unlike the historical log).
LIST_VEHICLES = """
SELECT id AS vehicle_id, status, battery_pct, lat, lon, is_offline, last_seen_at, active_anomaly_types
FROM vehicles
ORDER BY id
"""
