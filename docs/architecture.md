# Architecture

This document describes *how the code is organized* and the standards it follows. The *why* behind
the load-bearing choices lives in [`adr/0001-fleet-telemetry-architecture.md`](adr/0001-fleet-telemetry-architecture.md);
the concurrency reasoning lives in [`concurrency-and-isolation.md`](concurrency-and-isolation.md);
endpoint contracts live in [`api-contract.md`](api-contract.md).

> **Status:** implemented. The structure below matches the shipped `backend/` and `frontend/`
> trees; 17 backend tests and 3 Playwright e2e tests pass. See the [README](../README.md) to run it.

## 1. System at a glance

```
50 vehicles ──POST /telemetry──▶  FastAPI (asyncpg pool)  ──SQL──▶  PostgreSQL 16
                                        │  anomaly rules (inline)        ▲
                                        │  background staleness sweep ───┘
React dashboard  ──GET (poll 1.5s)──▶  REST + /scalar docs
```

See [`diagrams/01-system-context.md`](diagrams/01-system-context.md) for the rendered diagram.

## 2. Backend — Vertical Slice Architecture

The backend is organized **by feature/request**, not by technical layer. Each slice owns its
request end-to-end: routing, validation (Pydantic), business logic, and SQL. The guiding rule is
Bogard's: *minimize coupling between slices, maximize coupling within a slice.* Adding an endpoint
means adding a folder — not editing a shared `services/` or `repositories/` layer.

```
backend/
├── app/
│   ├── main.py                     # app factory: lifespan (pool, schema, sweep), Scalar mount, routers
│   ├── core/                       # cross-cutting INFRASTRUCTURE only (not business logic)
│   │   ├── config.py               # settings + anomaly thresholds (env-overridable)
│   │   ├── db.py                   # asyncpg pool + transaction helper
│   │   └── zones.py                # ZONES constant (the 20 named zones)
│   └── features/                   # one folder per vertical slice
│       ├── telemetry/
│       │   ├── router.py           # POST /telemetry, POST /telemetry/batch
│       │   ├── schemas.py          # TelemetryEvent in/out (Pydantic)
│       │   ├── ingest.py           # the slice: insert + snapshot upsert + zone counter + detection
│       │   └── anomaly_rules.py    # threshold + stateful rules (slice-local)
│       ├── vehicles/
│       │   ├── router.py           # POST /vehicles/{id}/status, GET /vehicles
│       │   ├── status_update.py    # the atomic fault command (single source of truth)
│       │   └── list_vehicles.py    # dashboard read (latest anomaly via DISTINCT ON)
│       ├── zones/
│       │   └── router.py           # GET /zones/counts
│       ├── anomalies/
│       │   └── router.py           # GET /anomalies?vehicle_id&start&end&limit
│       └── fleet/
│           └── router.py           # GET /fleet/state (per-status counts)
├── tests/                          # concurrency tests = the proof of the ADR's claims
├── simulate.py                     # 50-vehicle burst simulator
└── schema.sql                      # tables + indexes + ZONES seed (idempotent)
```

**The one deliberate cross-slice dependency.** The fault invariant (cancel mission + open
maintenance, atomically) must have exactly one implementation. It lives in
`vehicles/status_update.py`. When a telemetry event arrives with `status = fault`, the telemetry
slice *delegates* to that command rather than duplicating it. This is DRY winning over slice purity
for a critical invariant — an intentional, documented exception, not an accident. Everything else
stays slice-local.

**Batch ingest.** `POST /telemetry/batch` processes each event in its **own transaction**
(independent, best-effort): a malformed or stale event is skipped without aborting the rest, and the
response is a per-event result array. It is a throughput convenience over the single-event path
(which already handles concurrent bursts) and shares the exact same ingest logic. Full contract in
[`api-contract.md`](api-contract.md).

## 3. Frontend — Feature-Sliced Design + atomic design

```
frontend/src/
├── app/                 # providers (QueryClient), router, global styles, entry
├── pages/
│   └── dashboard/       # composes the widgets into the page
├── widgets/             # self-contained UI chunks (ORGANISMS)
│   ├── fleet-grid/      # 50 vehicle cards: status + battery + latest anomaly
│   ├── zone-counters/   # live per-zone entry counts
│   └── fleet-summary/   # per-status totals
├── entities/            # business domains (MODEL = zod schemas + inferred types, API = fetchers)
│   ├── vehicle/
│   ├── anomaly/
│   └── zone/
├── features/            # user interactions with business value (kept minimal — YAGNI)
└── shared/
    ├── ui/              # shadcn primitives (ATOMS) + small composed MOLECULES
    ├── api/             # base fetch client (base URL, error mapping)
    ├── lib/             # custom hooks (polling) + pure helpers (formatters, battery color)
    └── config/          # constants (poll interval, thresholds for display)
```

**Import rule (enforced by convention + ESLint boundaries):** a module may only import from layers
**strictly below** it. `widgets` may use `entities` and `shared`; `entities` may use `shared`;
`shared` imports nothing upward. Slices on the same layer never import each other.

**How atomic design maps onto FSD.** FSD answers *where business code lives*; atomic design answers
*how components compose*. They are orthogonal and coexist: shadcn primitives (`Button`, `Card`,
`Badge`) are **atoms** in `shared/ui`; small composed pieces (a `BatteryIndicator`, a
`StatusBadge`) are **molecules** (in `shared/ui` if generic, or `entities/*/ui` if domain-bound);
`widgets/*` are **organisms**; `pages/*` are **templates/pages**.

**Validation & types.** Each entity defines its zod schema in `entities/<x>/model`. The API layer
parses responses through the schema, so types are *inferred* (`z.infer`) and the boundary is
validated at runtime — a single source of truth for shape and types.

**Data sources.** The fleet grid's per-vehicle *latest anomaly* comes from `GET /vehicles`
(a `DISTINCT ON (vehicle_id) … ORDER BY detected_at DESC` join), while the filterable
`GET /anomalies` endpoint backs time-range queries. Two deliberately separate sources, so the live
grid stays a single cheap request and the anomaly history stays independently queryable.

## 4. Tech stack

| Layer        | Choice                                   | Note                                                  |
| ------------ | ---------------------------------------- | ----------------------------------------------------- |
| API          | FastAPI (async)                          | native async, OpenAPI out of the box                  |
| DB driver    | `asyncpg`                                | fast, async, raw SQL keeps locking legible            |
| Database     | PostgreSQL 16                            | row locks, MVCC, partial unique indexes               |
| API docs     | `scalar-fastapi` at `/scalar`            | browsable live contract                               |
| Frontend     | React + TypeScript + Vite                | fast dev loop                                         |
| Server state | TanStack Query (polling)                 | caching, dedup, `refetchInterval`                     |
| UI           | shadcn/ui + Tailwind                     | accessible primitives, atomic composition             |
| Validation   | zod                                      | runtime validation + inferred types                  |
| E2E          | Playwright                               | browser verification + deliverable test suite         |
| Orchestration| `docker-compose`                         | one-command run                                       |

## 5. Coding standards

- **Clean code, DRY, YAGNI, SOLID where it earns its keep.** Single-responsibility per slice/module;
  dependencies injected at the edges (the pool, config); no speculative abstractions.
- **Comments are a last resort.** Code should read clearly on its own; comment only where intent is
  genuinely non-obvious (e.g. *why* a lock is taken, a subtle SQL guard). No narrating-the-obvious.
- **Validate only at boundaries** (request bodies, external contract) — trust internal calls.
- **No defensive code for impossible states.** Lean on framework and DB guarantees.

## 6. Test strategy

- **Backend concurrency tests** are first-class — they *prove* the ADR's claims (no lost zone
  increments; exactly-once maintenance under duplicate faults). They run real concurrent requests
  against a real Postgres.
- **Anomaly-rule unit tests** cover each rule and its threshold edges.
- **Frontend Playwright e2e** verifies the dashboard renders and updates; screenshots are captured
  and read back during development to close the build→verify loop.
