CREATE TABLE IF NOT EXISTS vehicles (
  id                   text PRIMARY KEY,
  status               text NOT NULL DEFAULT 'idle',
  battery_pct          int  NOT NULL DEFAULT 100,
  lat                  double precision,
  lon                  double precision,
  speed_mps            double precision NOT NULL DEFAULT 0,
  last_timestamp       timestamptz,
  last_seen_at         timestamptz NOT NULL DEFAULT now(),
  is_offline           boolean NOT NULL DEFAULT false,
  active_anomaly_types text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS telemetry (
  id           bigserial PRIMARY KEY,
  vehicle_id   text NOT NULL,
  ts           timestamptz NOT NULL,
  lat          double precision,
  lon          double precision,
  battery_pct  int  NOT NULL,
  speed_mps    double precision NOT NULL,
  status       text NOT NULL,
  error_codes  text[] NOT NULL DEFAULT '{}',
  zone_entered text,
  received_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_ts ON telemetry (vehicle_id, ts DESC);

CREATE TABLE IF NOT EXISTS zone_counts (
  zone_id     text PRIMARY KEY,
  entry_count bigint NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS anomalies (
  id          bigserial PRIMARY KEY,
  vehicle_id  text NOT NULL,
  type        text NOT NULL,
  severity    text NOT NULL,
  detected_at timestamptz NOT NULL DEFAULT now(),
  details     jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_anomalies_vehicle_detected ON anomalies (vehicle_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected        ON anomalies (detected_at DESC);

CREATE TABLE IF NOT EXISTS missions (
  id         bigserial PRIMARY KEY,
  vehicle_id text NOT NULL,
  status     text NOT NULL DEFAULT 'active'
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_mission_per_vehicle
  ON missions (vehicle_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS maintenance (
  id          bigserial PRIMARY KEY,
  vehicle_id  text NOT NULL,
  opened_at   timestamptz NOT NULL DEFAULT now(),
  reason      text,
  status      text NOT NULL DEFAULT 'open',
  resolved_at timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_open_maintenance_per_vehicle
  ON maintenance (vehicle_id) WHERE status = 'open';

-- Seeds (idempotent) --------------------------------------------------------
-- zone_counts is seeded from the Python ZONES constant in app/core/db.py (single source of truth).

INSERT INTO vehicles (id)
  SELECT 'v-' || g FROM generate_series(1, 50) AS g
ON CONFLICT (id) DO NOTHING;

INSERT INTO missions (vehicle_id, status)
  SELECT 'v-' || g, 'active' FROM generate_series(1, 50) AS g
ON CONFLICT (vehicle_id) WHERE status = 'active' DO NOTHING;
