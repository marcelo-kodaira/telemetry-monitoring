export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const POLL_INTERVAL_MS = 1500;

// Mirror the backend anomaly thresholds (backend config.py: battery_critical_pct / battery_low_pct).
// Must stay in sync with the backend; the long-term fix is generating these from the API schema.
export const BATTERY_CRITICAL_PCT = 5;
export const BATTERY_LOW_PCT = 15;
