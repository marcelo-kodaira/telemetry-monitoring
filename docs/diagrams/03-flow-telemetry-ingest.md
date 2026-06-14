# 03 — Telemetry Ingest Flow

One `POST /telemetry` runs as a single transaction: append the event, load the previous snapshot,
run anomaly rules, persist anomalies, increment the zone counter if present, and upsert the current
snapshot. If the event carries `status = fault`, it delegates to the atomic fault command (flow 04).

```mermaid
sequenceDiagram
    autonumber
    participant V as Vehicle
    participant API as FastAPI (telemetry slice)
    participant DB as PostgreSQL

    V->>API: POST /telemetry {event}
    API->>API: validate body (Pydantic); zone_entered in ZONES or null
    API->>DB: BEGIN (READ COMMITTED)
    API->>DB: SELECT prev snapshot (status, battery, lat, lon, last_timestamp)
    API->>DB: INSERT INTO telemetry (...)
    API->>API: run rules — thresholds + stateful diff vs prev snapshot
    opt anomalies detected
        API->>DB: INSERT INTO anomalies (type, severity, details)
    end
    opt zone_entered not null
        API->>DB: UPDATE zone_counts SET entry_count = entry_count + 1
    end
    API->>DB: INSERT vehicles ... ON CONFLICT (id) DO UPDATE ... WHERE newer ts
    opt status == fault
        API->>API: delegate to fault command (flow 04, same txn)
    end
    API->>DB: COMMIT
    API-->>V: 202 Accepted {detected_anomalies}
```

**Why inline.** At ~50 events/s the previous snapshot is already loaded for the upsert, so
detection is essentially free and gives sub-second ("real-time") anomalies. At scale this moves to
a stream processor (see ADR Q3).
