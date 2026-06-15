# Concurrency & Isolation

This is the heart of the exercise. For each concurrency-sensitive operation we state the
**scenario**, the **naive approach that is wrong**, **our approach**, the **isolation level it
relies on**, and the **test that proves it**. All of it runs on PostgreSQL's default
**READ COMMITTED** isolation; we add narrower locks only where an operation needs them.

> Principle: reach for the *narrowest* correct mechanism. A global `SERIALIZABLE` setting or one
> big application mutex would "work" but would serialize unrelated work and hide the reasoning.

---

## 1. Zone-entry counter — "every entry must be counted"

**Scenario.** At shift change, many vehicles cross into `charging_bay_1` in the same second. Each
emits a telemetry event with `zone_entered = "charging_bay_1"`. Every one must increment the count.

**Naive (wrong).** Read-modify-write in the application:

```python
row = await conn.fetchrow("SELECT entry_count FROM zone_counts WHERE zone_id=$1", z)
await conn.execute("UPDATE zone_counts SET entry_count=$1 WHERE zone_id=$2", row[0] + 1, z)
```

Two events both read `N`, both write `N+1` → **one entry is lost**. This is the textbook
lost-update anomaly.

**Our approach.** A single atomic statement, in the same transaction as the telemetry insert:

```sql
UPDATE zone_counts SET entry_count = entry_count + 1 WHERE zone_id = $1;
```

Under READ COMMITTED, when two transactions update the *same row*, the second blocks until the
first commits, then re-reads the latest committed value and applies `+ 1` on top of it. The read
and the write are fused in one statement holding a row lock, so no update can be lost. The 20 zones
are seeded at startup, so the row always exists.

Mechanically this is PostgreSQL's **EvalPlanQual** re-evaluation: the blocked statement re-fetches
the latest committed row version and re-checks its `WHERE`. The guarantee holds *precisely because*
`WHERE zone_id = $1` filters on an **immutable key** — re-evaluation always re-matches the same row.
The pattern would **not** be safe if the `WHERE` referenced the mutated counter column, in which
case a re-evaluated row could be silently skipped. We rely on the immutable-key property here.

**Durable backstop.** The append-only `telemetry` table records `zone_entered` for every event, so
counts are fully reconstructable (`SELECT zone_entered, count(*) … GROUP BY zone_entered`). The
counter is the O(1) read path; the log is the source of truth.

**Isolation relied on.** READ COMMITTED + implicit row lock from the `UPDATE`.

**Proof.** `tests/test_zone_counter_concurrency.py`: fire *N* concurrent `POST /telemetry` events
all entering the same zone; assert `GET /zones/counts` returns exactly `N`.

See [`diagrams/05-flow-zone-counter.md`](diagrams/05-flow-zone-counter.md).

## 2. Fault transition — atomic mission cancel + maintenance record

**Scenario.** A vehicle transitions to `fault`. Its active mission must be cancelled and a
maintenance record opened — atomically. Duplicate fault events (a re-emit, or a status POST racing
a telemetry-borne fault) must not produce two maintenance records.

**Naive (wrong).** Three separate statements (or three endpoints) with no lock:

```text
UPDATE vehicles SET status='fault' …;     -- txn A
UPDATE missions SET status='cancelled' …; -- txn B  (crash here → faulted vehicle, live mission)
INSERT INTO maintenance …;                -- txn C  (duplicate fault → second record)
```

**Our approach.** One transaction, pessimistic row lock, idempotency check, DB-level guard:

```sql
BEGIN;                                                        -- READ COMMITTED
  SELECT status FROM vehicles WHERE id = $1 FOR UPDATE;        -- lock this vehicle row
  -- if status is already 'fault' → COMMIT and return (idempotent no-op)
  UPDATE vehicles  SET status = 'fault' WHERE id = $1;
  UPDATE missions  SET status = 'cancelled'
         WHERE vehicle_id = $1 AND status = 'active';
  INSERT INTO maintenance (vehicle_id, opened_at, reason, status)
         VALUES ($1, now(), $2, 'open');                      -- guarded by partial unique index
COMMIT;
```

`SELECT … FOR UPDATE` serializes concurrent fault transitions **for that vehicle** (other vehicles
proceed in parallel — the lock is one row). This relies on the row existing: the 50 vehicles are
**seeded at startup**, so the lock always engages. (A `FOR UPDATE` that matches zero rows acquires no
lock; for a hypothetical unseen id the command first runs `INSERT … ON CONFLICT (id) DO NOTHING` so
there is a row to lock. The partial unique index guarantees exactly-once maintenance regardless.) The first transaction sets `fault`; the second acquires
the lock afterward, re-reads `status = 'fault'`, and short-circuits → exactly one maintenance
record. As a hard backstop independent of application logic:

```sql
CREATE UNIQUE INDEX uq_open_maintenance_per_vehicle
  ON maintenance (vehicle_id) WHERE status = 'open';
```

**Why not `SERIALIZABLE`?** A per-vehicle row lock already provides the needed serialization at
lower cost than transaction-retry (`40001`) semantics. We pay only for the contention that actually
exists (same vehicle), not global serialization.

**Isolation relied on.** READ COMMITTED + `SELECT … FOR UPDATE` + partial unique index.

**Proof.** `tests/test_fault_transition.py`: fire concurrent duplicate `fault` requests for one
vehicle; assert exactly one `open` maintenance record and the mission cancelled exactly once.

See [`diagrams/04-flow-fault-transition.md`](diagrams/04-flow-fault-transition.md).

## 3. Fleet aggregate — per-status counts, safe under concurrent updates

**Scenario.** `GET /fleet/state` returns counts per status while vehicles are changing status
concurrently. The result must be internally consistent — no torn or double-counted reads.

**Our approach.** A plain aggregate query:

```sql
SELECT status, count(*) FROM vehicles GROUP BY status;
```

Under MVCC, this **single statement** reads a **consistent snapshot** — READ COMMITTED takes a fresh
snapshot per statement: it sees only committed rows, never blocks writers, and never tears. (Two
successive aggregate queries in one transaction may legitimately differ; each individual response is
internally consistent, which is exactly what the endpoint needs.) For 50 rows it is sub-millisecond.
No counter to drift, no lock to hold.

**Why not maintained counters?** At 50 vehicles a maintained counter is pure downside — another
thing to keep transactionally in sync and a source of drift bugs. The `GROUP BY` is correct and
simplest. Maintained/cached counters are the *scale* answer (see the ADR's Q3 table), not the slice
answer.

**Isolation relied on.** MVCC snapshot (READ COMMITTED is sufficient — each statement is consistent).

## 4. Telemetry ingestion under burst — vehicle snapshot upsert

**Scenario.** Bursts of concurrent `POST`s. Each event also updates the vehicle's "current"
snapshot (status, battery, position, last-seen) used by the dashboard and the aggregate.

**Our approach.** Append-only insert (no contention — distinct rows) plus a guarded upsert of the
snapshot:

```sql
INSERT INTO vehicles (id, status, battery_pct, lat, lon, last_timestamp, last_seen_at)
VALUES ($1, $2, $3, $4, $5, $6, now())
ON CONFLICT (id) DO UPDATE SET
  status = excluded.status, battery_pct = excluded.battery_pct,
  lat = excluded.lat, lon = excluded.lon,
  last_timestamp = excluded.last_timestamp, last_seen_at = now()
WHERE excluded.last_timestamp > vehicles.last_timestamp;   -- drop out-of-order events
```

Events for *different* vehicles touch different rows → full parallelism. Events for the *same*
vehicle (rare; one vehicle emits ~1/s) serialize on the row lock, and the `WHERE` guard prevents a
delayed older event from clobbering newer state. The connection **pool** (asyncpg, sized ~10–20
connections) provides the concurrency for the burst; requests beyond the pool queue asynchronously
rather than error; PostgreSQL handles the rest.

Two subtleties worth naming: a stale (guard-false) event is a **silent no-op** — locked, not
updated, not returned — so the caller cannot distinguish "applied" from "dropped as stale" via
rows-affected without checking. And two concurrent *first* inserts of the same new id are resolved
atomically by `ON CONFLICT`'s speculative insertion (one inserts, the other takes the `DO UPDATE`
branch), not by "distinct rows."

**Isolation relied on.** READ COMMITTED + row lock on conflict.

See [`diagrams/03-flow-telemetry-ingest.md`](diagrams/03-flow-telemetry-ingest.md).

## 5. Summary table

| Operation              | Mechanism                                   | Isolation             | Guarantee                         |
| ---------------------- | ------------------------------------------- | --------------------- | --------------------------------- |
| Zone counter           | `UPDATE … = … + 1`                          | READ COMMITTED + row lock | no lost updates               |
| Fault transition       | `SELECT … FOR UPDATE` + idempotency + uniq  | READ COMMITTED + row lock | atomic, exactly-once          |
| Fleet aggregate        | `GROUP BY` count                            | MVCC snapshot         | consistent, lock-free             |
| Snapshot upsert        | `INSERT … ON CONFLICT … WHERE newer`        | READ COMMITTED + row lock | newest-wins, no clobber       |
| Telemetry insert       | plain `INSERT`                              | none needed           | append-only, contention-free      |
| Anomaly / recent query | indexed read                                | MVCC snapshot         | consistent, lock-free             |
