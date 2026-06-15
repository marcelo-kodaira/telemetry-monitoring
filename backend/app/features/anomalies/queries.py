"""SQL for the anomalies slice."""
from app.core.domain import AnomalyType, Severity

SELECT_ANOMALIES = "SELECT id, vehicle_id, type, severity, detected_at, details FROM anomalies"

# Mark vehicles silent longer than the staleness window offline and emit one stale_offline anomaly
# each, in a single statement. Type/severity come from the enums (single source of truth).
MARK_NEWLY_OFFLINE = f"""
WITH newly_offline AS (
    UPDATE vehicles SET is_offline = true
    WHERE NOT is_offline AND last_seen_at < now() - ($1 || ' seconds')::interval
    RETURNING id
)
INSERT INTO anomalies (vehicle_id, type, severity, details)
SELECT id, '{AnomalyType.STALE_OFFLINE}', '{Severity.CRITICAL}', '{{}}'::jsonb FROM newly_offline
"""
