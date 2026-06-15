# 02 — Data Model (ER)

Six tables. `telemetry` is the append-only event log (source of truth). `vehicles` holds the
current snapshot per vehicle (the dashboard/aggregate read model). `zone_counts` is the O(1)
counter, reconstructable from `telemetry.zone_entered`.

```mermaid
erDiagram
    VEHICLES ||--o{ TELEMETRY   : emits
    VEHICLES ||--o{ ANOMALIES   : flagged_by
    VEHICLES ||--o{ MISSIONS    : assigned
    VEHICLES ||--o{ MAINTENANCE : opens

    VEHICLES {
        text   id PK
        text   status
        int    battery_pct
        float  lat
        float  lon
        timestamptz last_timestamp
        timestamptz last_seen_at
        bool   is_offline
    }
    TELEMETRY {
        bigserial id PK
        text   vehicle_id FK
        timestamptz ts
        float  lat
        float  lon
        int    battery_pct
        float  speed_mps
        text   status
        text   error_codes "text[]"
        text   zone_entered "nullable"
        timestamptz received_at
    }
    ZONE_COUNTS {
        text zone_id PK
        bigint entry_count
    }
    ANOMALIES {
        bigserial id PK
        text   vehicle_id FK
        text   type
        text   severity
        timestamptz detected_at
        jsonb  details
    }
    MISSIONS {
        bigserial id PK
        text   vehicle_id FK
        text   status "active|cancelled|done"
    }
    MAINTENANCE {
        bigserial id PK
        text   vehicle_id FK
        timestamptz opened_at
        text   reason
        text   status "open|resolved"
        timestamptz resolved_at "nullable"
    }
```

**Key indexes & constraints.**
- `anomalies (vehicle_id, detected_at)` — fast "recent anomalies by vehicle and time range".
- `telemetry (vehicle_id, ts)` — per-vehicle history and dedupe by `(vehicle_id, ts)`.
- `maintenance` partial unique: `UNIQUE (vehicle_id) WHERE status = 'open'` — at most one open
  record per vehicle (the fault-idempotency backstop).
- `missions` partial unique: `UNIQUE (vehicle_id) WHERE status = 'active'` — at most one active
  mission per vehicle.
- `zone_counts` seeded with the 20 `ZONES` at startup so the atomic `UPDATE` always hits a row.
- The 50 `vehicles` (`v-1…v-50`) are seeded at startup too, so the fault-path `SELECT … FOR UPDATE`
  always finds a row to lock.
- `vehicles.is_offline` is maintained by the background staleness sweep — set when `last_seen_at` is
  older than the 10 s window, cleared on the next telemetry event. Offline state is *stored* (not
  only derived) so the dashboard renders it without recomputing.
- `missions.status`: `active` (managed here) and `cancelled` (set on fault) are the lifecycle this
  slice drives; `done` is reserved for external mission completion (missions are assigned
  externally) and is out of slice scope.
