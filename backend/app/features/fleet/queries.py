"""SQL for the fleet slice."""

STATUS_COUNTS = "SELECT status, count(*) AS n FROM vehicles GROUP BY status"
OFFLINE_COUNT = "SELECT count(*) FROM vehicles WHERE is_offline"
TOTAL_COUNT = "SELECT count(*) FROM vehicles"
