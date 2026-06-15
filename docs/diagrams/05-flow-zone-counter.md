# 05 — Zone Counter Flow (concurrent, no lost update)

Two vehicles cross into `charging_bay_1` in the same instant. Both increments must land. The atomic
`UPDATE … = … + 1` row-locks the zone row, so the second transaction re-reads the latest committed
value before applying its increment.

```mermaid
sequenceDiagram
    autonumber
    participant A as Vehicle A
    participant B as Vehicle B
    participant API as FastAPI
    participant DB as PostgreSQL (row charging_bay_1, count=7)

    par concurrent arrivals (same second)
        A->>API: POST /telemetry zone_entered=charging_bay_1
    and
        B->>API: POST /telemetry zone_entered=charging_bay_1
    end

    API->>DB: txn A: UPDATE zone_counts SET entry_count=entry_count+1 WHERE zone_id='charging_bay_1'
    API->>DB: txn B: UPDATE ... same row
    Note over DB: txn B blocks on txn A's row lock
    DB-->>API: txn A commits (7 -> 8)
    Note over DB: txn B unblocks, re-reads latest committed (8), applies +1
    DB-->>API: txn B commits (8 -> 9)
    Note over DB: Both counted. Read-modify-write in app code would have lost one.
```

**Proof.** `tests/test_zone_counter_concurrency.py` fires *N* concurrent same-zone events and
asserts the count equals exactly *N*. The append-only `telemetry` log lets counts be rebuilt if
ever needed.
