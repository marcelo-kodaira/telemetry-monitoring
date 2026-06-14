# ADR-0001 — Fleet Telemetry Monitoring: Architecture & Key Decisions

|              |                                                                                  |
| ------------ | -------------------------------------------------------------------------------- |
| **Status**   | Accepted                                                                         |
| **Date**     | 2026-06-14                                                                       |
| **Deciders** | Marcelo Almeida (engineering owner)                                              |
| **AI pair**  | Claude (Opus 4.8) — alternatives analysis, drafting, adversarial review of claims |
| **Format**   | MADR-influenced (Context → Drivers → Decisions → Consequences), consolidated      |

> This is a *consolidated* decision record: one document covering the load-bearing
> decisions for a single, cohesive vertical slice. Each decision lists the **alternatives
> considered and why they were rejected**, as required. Diagrams and flows live in
> [`../diagrams/`](../diagrams/); the isolation reasoning is expanded in
> [`../concurrency-and-isolation.md`](../concurrency-and-isolation.md).

---

## 1. Context and Problem Statement

We are building a vertical slice of a fleet-monitoring backend (plus a small dashboard) for
**50 autonomous industrial vehicles emitting telemetry at 1 Hz** — roughly 50 events/second
steady-state, with bursts when vehicles converge (e.g. shift change at the charging bays).

The service must, under concurrent load:

1. **Ingest** telemetry via POST, absorbing bursts of concurrent writes.
2. **Persist** events durably.
3. **Detect anomalies in real time.**
4. **Count zone traversals** such that *every* `zone_entered` event is counted, even when many
   vehicles enter the same zone in the same instant.
5. **Handle `fault` transitions atomically** — cancel the active mission and open a maintenance
   record as one indivisible unit.
6. **Query recent anomalies** by vehicle and time range.
7. **Report aggregate fleet state** (per-status counts) safely under concurrent updates.

The brief states explicitly that the ADR and the AI-interaction log are valued *as much as the
code*, and it deliberately leaves several requirements open. Above all, the exercise probes one
competency: **do we reason correctly about concurrency and choose the right isolation strategy?**
Every decision below is made through that lens.

> **Implementation status (2026-06-14).** This is the *design* phase: decisions precede code. The
> repository currently holds these design documents. The backend, dashboard, `schema.sql`,
> `docker-compose.yml`, and tests described below are the **acceptance criteria** for the
> implementation that follows — not yet-shipped artifacts. Present-tense descriptions denote
> intended behavior.

## 2. Decision Drivers

- **DR1 — Concurrency correctness.** No lost zone-entry increments; atomic and *idempotent* fault
  handling; aggregate reads that never tear under concurrent writes. This is the primary axis the
  exercise grades.
- **DR2 — Demonstrability.** A reviewer should be able to *see* the isolation mechanism (the lock,
  the atomic statement) in the code, not have it hidden behind an ORM's abstraction.
- **DR3 — Real-time anomaly detection** with a definition we can defend.
- **DR4 — Runnability.** One command to start; an unambiguous README. "We will run your code."
- **DR5 — Change isolation & maintainability.** Adding a feature must not ripple through shared
  layers — pushes us toward vertical slices (backend) and Feature-Sliced Design (frontend).
- **DR6 — Time budget / YAGNI.** A 5–6h slice, not a platform. Every gold-plating temptation is
  cut and recorded in §6 (Q4).
- **DR7 — AI-driven development.** The process is a deliverable: design → ADR → tests-as-guardrails
  → implement → browser-verify loop → adversarial review. See [`../ai-driven-sdlc.md`](../ai-driven-sdlc.md).

## 3. Decisions

| #  | Decision                                                                                          |
| -- | ------------------------------------------------------------------------------------------------- |
| D1 | Backend = **FastAPI + `asyncpg` + raw SQL**, organized as **vertical slices** (by feature)        |
| D2 | Persistence = **PostgreSQL 16**                                                                    |
| D3 | Concurrency strategy = **targeted row locks + atomic SQL under READ COMMITTED** (not global SERIALIZABLE) |
| D4 | Zone counter = **atomic `UPDATE … +1` inside the ingest transaction**, telemetry log as backstop  |
| D5 | Fault transition = **single transaction, `SELECT … FOR UPDATE`, idempotent, partial-unique guard**|
| D6 | Anomaly model = **hybrid**: instantaneous thresholds + stateful diffs + background staleness sweep|
| D7 | Frontend = **React + TS + Vite**, **FSD + atomic design**, **shadcn/ui**, **zod**, **TanStack Query**|
| D8 | Real-time transport = **short-interval polling (~1.5 s)**                                          |

### D1 — FastAPI + asyncpg + raw SQL, as vertical slices

**Decision.** A FastAPI application using an `asyncpg` connection pool and hand-written SQL,
organized so each *request* (ingest telemetry, update status, get zone counts, …) is a
self-contained vertical slice under `app/features/<slice>/`. Cross-cutting infrastructure only
(DB pool, config, the `ZONES` constant) lives in `app/core/`.

**Alternatives considered & why rejected.**

- **Django REST Framework.** Rejected: heavier, opinionated toward a layered/ORM-centric design;
  its ORM hides exactly the locking and atomic statements this exercise wants us to demonstrate
  (DR2); async support is bolted-on rather than native.
- **FastAPI + SQLAlchemy async ORM.** A strong *production* choice and the maintainable default
  — but rejected *for this slice* because `with_for_update()` and `count = count + 1` get
  abstracted away; the concurrency story becomes "trust the ORM" instead of legible SQL (DR2).
  Recorded as the recommended migration path once the model stabilizes.
- **Flask.** Rejected: synchronous-first; weaker concurrency story for burst ingestion (DR1).
- **Layered architecture (controllers/services/repositories).** Rejected: forces every request
  through the same horizontal abstractions, coupling unrelated features through shared service and
  repository layers (DR5). Vertical slices "minimize coupling between slices, maximize coupling
  within a slice" (Bogard) — a new endpoint adds a folder instead of editing shared layers.

**Consequences.** *Good:* legible concurrency primitives; features are independently
understandable and testable; minimal indirection. *Bad:* raw SQL forgoes ORM safety nets
(mitigated by parameterized queries and tests); a genuinely shared invariant (fault handling) must
be deliberately placed to avoid duplication — see D5 and [`../architecture.md`](../architecture.md).
*Neutral:* a thin `core/db.py` helper standardizes transaction handling across slices.

### D2 — PostgreSQL 16

**Decision.** PostgreSQL, run via `docker-compose` so the whole stack starts with one command.

**Alternatives considered & why rejected.**

- **SQLite (WAL mode).** Tempting for zero-setup runnability (DR4). Rejected: SQLite serializes
  **all** writers (a single write lock for the whole database). That makes the zone counter
  *trivially* correct — but by side-stepping the very question the exercise asks. We would be
  demonstrating "the database has one big lock," not an isolation strategy. It also caps real
  concurrency and can't show row-level locking, `FOR UPDATE`, or MVCC snapshot reads.
- **In-memory store / dict + asyncio.Lock.** Rejected: no durability (req. #2), and an app-level
  lock is a single point of contention that does not survive a restart or scale horizontally.
- **A time-series DB (Timescale/Influx).** Rejected as premature (DR6/YAGNI). Noted as a scale
  path in §6 (Q3).

**Consequences.** *Good:* real row-level locks, `SELECT … FOR UPDATE`, MVCC snapshot reads, and
partial unique indexes — the full toolbox the exercise probes; `docker-compose up` keeps it
one-command runnable. *Bad:* a running container is required (vs a single file). *Neutral:* schema
is applied idempotently from `schema.sql` at startup (no migration tool for the slice).

### D3 — Targeted row locks + atomic SQL under READ COMMITTED

**Decision.** Use PostgreSQL's default **READ COMMITTED** isolation, and reach for the *narrowest*
correct mechanism per operation rather than one blunt global setting:

| Concern                         | Mechanism                                                                                          | Why it is correct                                                                                   |
| ------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Telemetry insert (diff vehicles)| plain `INSERT`, distinct rows                                                                      | no shared row → no contention                                                                        |
| Vehicle snapshot update         | `INSERT … ON CONFLICT (id) DO UPDATE … WHERE excluded.last_timestamp > vehicles.last_timestamp`         | conflict path takes a row lock; the guard drops out-of-order events                                  |
| **Zone counter**                | `UPDATE zone_counts SET entry_count = entry_count + 1 WHERE zone_id = $1` (same txn as ingest)     | the `UPDATE` row-locks and re-reads the latest committed value → concurrent increments **serialize, zero lost updates** |
| **Fault transition**            | one txn: `SELECT … FOR UPDATE` the vehicle → idempotency check → cancel mission → insert maintenance | pessimistic row lock serializes concurrent/duplicate fault events *for that vehicle* (vehicles are pre-seeded so the row exists and the lock engages); atomic; partial unique index is the lock-independent backstop |
| **Fleet aggregate**             | `SELECT status, count(*) … GROUP BY status`                                                        | MVCC snapshot → a consistent point-in-time count, never blocks writers, never tears                  |
| Recent-anomalies query          | indexed read on `(vehicle_id, detected_at)`                                                        | MVCC snapshot, lock-free                                                                              |

**Alternatives considered & why rejected.**

- **`SERIALIZABLE` everywhere.** Rejected: correct but pessimal here — it introduces
  serialization-failure retries (`40001`) on hot rows like the popular charging zones, hurting
  throughput (DR1) for no extra correctness over targeted row locks in these specific operations.
- **A single application-level mutex / `asyncio.Lock`.** Rejected: serializes unrelated work, is a
  single point of contention, and does not survive multiple app replicas (DR5).
- **Optimistic concurrency (version columns + retry).** Rejected for the zone counter: a hot,
  write-heavy counter would thrash on retries; pessimistic row locking is the right tool for a
  known hotspot.

**Consequences.** *Good:* maximal concurrency for non-conflicting work, correctness where it
matters, and each mechanism is visible and test-provable. *Bad:* the reasoning is per-operation
rather than one global knob — which is exactly why it is documented in
[`../concurrency-and-isolation.md`](../concurrency-and-isolation.md) and pinned by tests.

### D4 — Zone counter: atomic increment in the ingest transaction

**Decision.** When a telemetry event carries a non-null `zone_entered`, increment that zone's
counter with a single atomic statement **inside the same transaction** as the telemetry insert.
The append-only `telemetry` table (which records `zone_entered`) is the durable backstop: counts
are fully reconstructable by replaying it.

**Alternatives considered & why rejected.**

- **Read-modify-write in application code** (`SELECT count → +1 → UPDATE`). Rejected: the classic
  lost-update bug — two vehicles read the same value and both write `value+1`, losing one entry.
  This is the exact failure the requirement forbids.
- **Append-only event table + `COUNT(*)` only (no counter).** Bulletproof for "every entry
  counted" and fully auditable, but rejected *as the read path* because counts become an O(n)
  aggregate. Kept as the **backstop / source of truth**; the counter is the O(1) fast path.
- **Materialized view of counts.** Rejected: refresh lag means `GET /zones/counts` could read
  stale values; the live requirement wants immediacy.

**Consequences.** *Good:* O(1) reads, zero lost updates, reconstructable from the log. *Bad:* a
single counter row per zone is a potential hotspot at extreme scale (addressed in §6/Q3:
sharded counters). *Neutral:* the 20 zones are seeded at startup so the `UPDATE` always hits a row;
an unknown `zone_entered` is rejected at the boundary (422).

### D5 — Fault transition: one atomic, idempotent transaction

**Decision.** Transitioning a vehicle to `fault` runs as a single transaction:
`SELECT status FROM vehicles WHERE id = $1 FOR UPDATE` → if already `fault`, no-op (idempotent) →
set status `fault` → cancel the active mission → insert a maintenance record. A partial unique
index `UNIQUE (vehicle_id) WHERE status = 'open'` on `maintenance` is a hard database guarantee
against duplicates even if application logic is bypassed. **Precondition:** the 50 vehicles are
seeded at startup, so `SELECT … FOR UPDATE` always finds a row and the serialization actually
engages (a `FOR UPDATE` matching zero rows locks nothing); if an unseen id ever reached this path
the command first runs an idempotent `INSERT … ON CONFLICT (id) DO NOTHING` so a row exists to lock. This single command is the **one**
implementation of the invariant; a telemetry event arriving with `status = 'fault'` delegates to
it (DRY for a critical invariant, an intentional, documented exception to slice isolation).

**Alternatives considered & why rejected.**

- **Separate transactions / multiple endpoints** (update status, then cancel mission, then create
  maintenance). Rejected: non-atomic — a crash between steps leaves a faulted vehicle with a live
  mission or no maintenance record. The requirement says *atomically*.
- **No idempotency / no lock.** Rejected: two concurrent `fault` events for the same vehicle (a
  duplicate emit, or a status POST racing a telemetry-borne fault) would each cancel and each open
  a maintenance record → duplicates. `FOR UPDATE` + the status check + the partial unique index
  make exactly-once the invariant.
- **`SERIALIZABLE` for this path.** Rejected: a per-vehicle row lock already gives the needed
  serialization at lower cost than transaction-retry semantics.

**Consequences.** *Good:* exactly-once maintenance per fault episode, atomic, and other vehicles
proceed in parallel (the lock is on one row). *Bad:* a faulted vehicle is treated as terminal until
maintenance is resolved — a documented assumption (§5/Q2). *Neutral:* non-fault status updates take
a cheap fast-path `UPDATE` and skip the transactional ceremony.

### D6 — Anomaly model: hybrid detection

**Decision.** "Anomaly" = a condition that warrants operator attention and *cannot wait* for a
human to read a chart. We detect across three axes; event-driven rules run **inline in the ingest
transaction** (the previous snapshot is already loaded), and absence-of-data runs in a background
sweep:

| Type                 | Rule                                                  | Axis        | Default       | Severity  |
| -------------------- | ----------------------------------------------------- | ----------- | ------------- | --------- |
| `critical_battery`   | `battery_pct ≤ 5`                                      | threshold   | 5 %           | critical  |
| `low_battery`        | `battery_pct ≤ 15`                                    | threshold   | 15 %          | warning   |
| `fault_status`       | `status == fault`                                     | threshold   | —             | critical  |
| `error_code_present` | `error_codes` non-empty                               | threshold   | —             | warning   |
| `overspeed`          | `speed_mps > 3.0`                                     | threshold   | 3.0 m/s       | warning   |
| `state_inconsistent` | `speed_mps > 0` while `status ∈ {idle, charging}`     | threshold   | —             | warning   |
| `battery_drain`      | Δbattery/Δt drop steeper than threshold               | stateful    | > 2 %/s       | warning   |
| `charging_no_gain`   | `status == charging` and battery decreasing           | stateful    | —             | warning   |
| `position_jump`      | `haversine(prev, cur)/Δt` implies speed > physical max| stateful    | > 8 m/s impl. | critical  |
| `stale_offline`      | no telemetry for > N seconds                          | absence     | 10 s          | critical  |

**Thresholds reconciled.** The vehicles' physical top speed is ≈4 m/s. `overspeed` is a
*policy/safety* limit set intentionally below that (3.0 m/s — "faster than allowed here"); while
`position_jump` is a *physical-impossibility* limit set above it (implied speed > 8 m/s ≈ 2× physical
max, tolerant of GPS jitter — "this reading cannot be real"). They model different things, so the
gap between 3 and 8 m/s is expected, not a contradiction.

**Persistence is edge-triggered.** Event-driven anomalies are recorded on condition *entry* only —
when a rule transitions false→true between the previous snapshot and the current event — not on
every event while the condition persists. A vehicle stuck at 4 % battery yields one
`critical_battery` row, not one per second. This mirrors the staleness sweep, bounds row growth, and
makes "most recent anomaly per vehicle" meaningful.

**Offline detection.** A background sweep runs every 5 s; a vehicle whose `last_seen_at` is older
than the 10 s staleness window is marked `is_offline = true` and emits a single `stale_offline`
anomaly (both cleared and re-armed on the next telemetry event). Worst-case offline-detection
latency is therefore ≈ staleness window + sweep period ≈ **15 s** — the explicit bound on the
"absence" axis.

**Stateful rules and concurrency.** Stateful rules read the previous snapshot inside the ingest
transaction, under the same per-vehicle serialization as the snapshot upsert (D3), so concurrent
same-vehicle events cannot diff against a torn or racing prior state.

**Justification (the three axes).** (1) *Instantaneous health/safety thresholds* catch states a
human would page on. (2) *Physically-impossible or self-contradictory readings* (teleport,
charging-but-draining, moving-while-idle) catch sensor faults, spoofing, or model drift that
threshold rules miss. (3) *Absence of data* catches comms loss — a silent vehicle is often the most
dangerous one, and only a background sweep can detect "nothing arrived."

**Alternatives considered & why rejected.**

- **Pure per-event thresholds (stateless only).** Rejected: misses rate-based faults, impossible
  jumps, and offline vehicles — the failures an operator most needs.
- **Async queue / stream processor for detection.** Rejected for the slice (DR6); the right answer
  at scale (§6/Q3) but overkill at 50 events/s where the previous snapshot is already in hand.
- **ML / anomaly-scoring models.** Rejected: no labels, no baseline, and unjustifiable for a 5–6h
  slice (YAGNI). Rule-based detection is transparent and testable.

**Consequences.** *Good:* real-time (sub-second) for event rules, defensible coverage, transparent
rules, all thresholds are configurable constants. *Bad:* inline detection couples a little work to
the ingest path (cheap at this scale; moved off-path at scale). *Neutral:* the staleness sweep is
edge-triggered (emits once on online→offline) to avoid duplicate anomalies every interval.

### D7 / D8 — Frontend: FSD + atomic design, shadcn, zod, polling

**Decision.** React + TypeScript + Vite. **Feature-Sliced Design** for structure
(`app → pages → widgets → entities → shared`, lower-only imports), **atomic design** within the
component dimension (shadcn primitives = atoms in `shared/ui`, composed molecules, `widgets` =
organisms), **zod** for runtime validation + inferred types at the API boundary, **TanStack Query**
with `refetchInterval ≈ 1.5 s` for live updates, and **Playwright** for end-to-end tests.

**Alternatives considered & why rejected.**

- **WebSockets.** Rejected: overkill for a read-only dashboard fed by 1 Hz data; adds
  connection-state, reconnection, and fan-out complexity for no perceptible gain at this scale.
- **Server-Sent Events.** A reasonable middle ground (one-way push), but rejected for the slice:
  still more moving parts than needed when a 1.5 s poll is indistinguishable to a human. Recorded
  as the first scale step (§6/Q3).
- **Redux / Zustand for server state.** Rejected: TanStack Query owns server-state
  (caching/refetch/dedup); adding a client store would duplicate it (YAGNI/DRY).
- **Plain `fetch` without zod.** Rejected: the dashboard trusts an external contract; zod validates
  at the boundary and gives us inferred types for free.

**Consequences.** *Good:* simple, robust, stateless updates; clean domain boundaries; type-safe
boundary. *Bad:* up-to-1.5 s latency and steady polling traffic (negligible for 50 vehicles).
*Neutral:* polling interval is a single config value, trivially swapped for SSE later.

## 4. Confirmation (how we validate these decisions)

Decisions are only as good as their proof. Validation mechanisms:

- **Concurrency tests** are the evidence for D3–D5, not an afterthought:
  - fire *N* concurrent `POST`s entering the **same** zone → assert `entry_count == N`;
  - fire concurrent **duplicate** `fault` events for one vehicle → assert **exactly one**
    maintenance record and the mission cancelled exactly once.
- **`simulate.py`** drives 50 vehicles converging on the charging bays to reproduce the burst
  scenario from the brief.
- **Playwright e2e** verifies the dashboard renders fleet state, latest anomalies, and live zone
  counts; screenshots are read back during development to close the loop.
- **Scalar API docs** at `/scalar` act as the live, browsable contract for every endpoint.

## 5. The four required questions

**Q1 — The two–three most important decisions, and why.**
(1) **PostgreSQL + the targeted-isolation strategy (D2/D3)** — the spine of the whole exercise;
it's what makes "every entry counted" and "atomic fault handling" *true* rather than hopeful.
(2) **The hybrid anomaly model (D6)** — defining "anomaly" across health, physical-impossibility,
and absence axes is the judgment call that makes the feature meaningful. (3) **Vertical slices +
FSD (D1/D7)** — chosen so the system stays legible and each feature is independently
understandable, testable, and changeable.

**Q2 — What was unclear in the spec, and what we assumed.**

- *Timestamps & payload:* timestamps are client-provided ISO-8601 UTC (telemetry column `ts`); the
  server also stamps `received_at`. Each event carries `lat`/`lon`, `battery_pct`, `speed_mps`,
  `status`, `error_codes`, and `zone_entered` (per the brief) — `lat`/`lon` are what enable the
  `position_jump` haversine check. Out-of-order/duplicate events are possible → dedupe by
  `(vehicle_id, ts)` and guard the snapshot with a newer-`ts` check.
- *"Mission":* modelled minimally — at most one active mission per vehicle, assigned externally /
  seeded; we implement only cancel-on-fault.
- *"Maintenance record":* `{vehicle_id, opened_at, reason, status: open|resolved}`, at most one
  `open` per vehicle (partial unique index).
- *Vehicle registry:* the 50 vehicles (`v-1…v-50`) are **seeded at startup**, so the fault path
  always finds a row to lock; telemetry from an unknown id still self-registers via the snapshot
  upsert, but the seeded set is the precondition for the fault-transition lock.
- *`zone_entered`:* assumed it must be one of the 20 `ZONES`; an unknown value is rejected at the
  boundary (422) — validate only at system edges.
- *Fault terminality:* a faulted vehicle stays faulted until maintenance is resolved; later
  non-fault telemetry does not silently clear it.
- *Maintenance resolution is out of scope:* nothing in this slice transitions a vehicle out of
  `fault` or a maintenance record to `resolved` (no resolution endpoint), so the open-maintenance
  unique index is exercised only by fault entry — sufficient for the slice.
- *"Status update operation":* exposed as `POST /vehicles/{id}/status`; a telemetry event with
  `status = fault` delegates to the same command, so the invariant has a single source of truth.
- *Thresholds* (battery, speed, drain rate, teleport speed, staleness window) are configurable
  constants with justified defaults.
- *Deployment:* single region, single Postgres instance; no HA/auth assumed (trusted private
  network).

**Q3 — What changes if scale grows *significantly*.**
We define "significant" as **100×–1000×**: from 50 vehicles @ 1 Hz (≈50 msg/s) to 5k–50k vehicles
and/or 1 Hz → 10 Hz (≈5k–500k msg/s), multi-site, with months of retention.

| Dimension          | Today (slice)                       | At significant scale                                   |
| ------------------ | ----------------------------------- | ------------------------------------------------------ |
| Ingestion          | sync `INSERT` per request, pool     | front with a log/stream (Kafka/NATS/Kinesis) + batch writers; decouple accept from persist |
| Telemetry storage  | single Postgres table               | time-partitioning (native / Timescale), rollups, retention, cold tiering or OLAP store |
| Anomaly detection  | inline in ingest txn + bg sweep     | stream processor (Flink/Faust/Kafka Streams) keyed by vehicle with windowed state |
| Zone counter       | atomic single-row `UPDATE`          | sharded counters / per-shard rollups / Redis `INCR` / incremental materialization from the log |
| Fleet aggregate    | `GROUP BY` over 50 rows             | maintained counters (transactional or via CDC) / cached projection |
| Fault transition   | per-vehicle row lock                | unchanged pattern — shards cleanly by `vehicle_id`     |
| API tier           | single app process                  | stateless replicas behind a load balancer, PgBouncer pooling |
| Dashboard          | polling @ 1.5 s                     | SSE/WebSocket fan-out via pub/sub; server-side aggregation; backpressure |
| Delivery semantics | at-least-once + dedupe by (veh, ts) | idempotency keys, dedupe in the stream layer           |

**Q4 — What we deliberately left out, and why.**

- **AuthN/Z, TLS, rate limiting, multi-tenancy** — trusted private-network assumption; out of slice
  scope.
- **Real zone geometry / geofencing** — the edge client populates `zone_entered` (per the brief).
- **Alerting/notification routing** (paging/Slack/email) — anomalies are persisted and surfaced,
  not routed.
- **Historical analytics, charts, map view** — beyond the live-monitoring slice.
- **Full mission lifecycle** (assignment, completion, scheduling) — only cancel-on-fault is in
  scope.
- **Retention/archival/backup, Alembic migrations** — `schema.sql` applied idempotently suffices
  for the slice.
- **Horizontal-scale infra, exactly-once ingestion, observability stack** (metrics/tracing) —
  deferred to the scale path; basic structured logging only.
- **WebSockets and ML-based anomaly detection** — explicitly rejected above (D6/D8) as YAGNI.

## 6. Consequences (summary)

**Good.** The isolation strategy is correct *and legible*, and pinned by concurrency tests. The
architecture isolates change (slices/FSD). The stack runs with one command. The anomaly model is
defensible and transparent. The whole process is documented as an AI-driven SDLC.

**Bad / accepted trade-offs.** Raw SQL gives up ORM safety nets; inline detection couples a little
work to ingest; a single counter row per zone is a future hotspot; the fault path treats faults as
terminal. Each is bounded, justified above, and has a named scale path.

**Neutral.** No migration tool, no auth, single-region — appropriate for a slice, called out so a
reader knows they were choices, not oversights.

## 7. More information

- [`../architecture.md`](../architecture.md) — vertical slice + FSD + atomic design, repo map,
  coding standards, test strategy.
- [`../concurrency-and-isolation.md`](../concurrency-and-isolation.md) — per-operation isolation
  reasoning with SQL and the test that proves each claim.
- [`../api-contract.md`](../api-contract.md) — endpoint request/response/error contracts, query-param
  semantics, batch ingest behavior, and the Scalar curation plan.
- [`../diagrams/`](../diagrams/) — system context, ER model, and the ingest / fault / zone-counter
  sequence flows.
- [`../ai-driven-sdlc.md`](../ai-driven-sdlc.md) — how AI drove each phase of this build.
- References: M. Nygard, *Documenting Architecture Decisions* (2011); O. Zimmermann, *MADR Template
  Primer* (2022); J. Bogard, *Vertical Slice Architecture* (2018); *Feature-Sliced Design* docs.
