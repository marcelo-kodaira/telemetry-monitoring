# 04 — Fault Transition Flow

A `fault` transition cancels the active mission and opens a maintenance record **atomically and
idempotently**, under a per-vehicle row lock. Concurrent or duplicate fault events for the same
vehicle produce exactly one maintenance record.

```mermaid
sequenceDiagram
    autonumber
    participant C as Caller (status POST / telemetry fault)
    participant API as FastAPI (vehicles slice)
    participant DB as PostgreSQL

    C->>API: POST /vehicles/{id}/status {status: fault, reason}
    API->>DB: BEGIN (READ COMMITTED)
    API->>DB: SELECT status FROM vehicles WHERE id=$1 FOR UPDATE
    alt already fault (duplicate / race loser)
        API->>DB: COMMIT (no-op)
        API-->>C: 200 idempotent (no new record)
    else newly transitioning to fault
        API->>DB: UPDATE vehicles SET status='fault'
        API->>DB: UPDATE missions SET status='cancelled' WHERE vehicle_id=$1 AND status='active'
        API->>DB: INSERT INTO maintenance (vehicle_id, opened_at, reason, status='open')
        API->>DB: COMMIT
        API-->>C: 200 {maintenance_id, mission_cancelled: true}
    end

    Note over DB: FOR UPDATE serializes concurrent faults for THIS vehicle only<br/>(vehicles are pre-seeded, so the row exists and the lock engages).
    Note over DB: Partial unique index uq_open_maintenance_per_vehicle is a hard backstop:<br/>at most one open maintenance record even under races.
```

**Single source of truth.** This command is the *only* implementation of the fault invariant. The
telemetry slice delegates to it when an event arrives with `status = fault`, so the invariant is
never duplicated (DRY for a critical operation — see [`../architecture.md`](../architecture.md) §2).
