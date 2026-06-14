# 01 — System Context

Containers and the data that flows between them. The edge clients populate `zone_entered`; the API
owns persistence, anomaly detection, and the concurrency-safe operations; the dashboard is a
read-only poller.

```mermaid
flowchart LR
    subgraph Fleet["Fleet — 50 vehicles @ 1 Hz"]
        V["Vehicle edge client<br/>(emits telemetry,<br/>sets zone_entered on crossing)"]
    end

    subgraph Service["Telemetry Monitoring Service"]
        API["FastAPI app<br/>(asyncpg pool, vertical slices)"]
        SWEEP["Background staleness sweep<br/>(asyncio task)"]
        DOCS["/scalar API docs"]
    end

    DB[("PostgreSQL 16<br/>vehicles · telemetry · zone_counts<br/>anomalies · missions · maintenance")]

    subgraph UI["Operator dashboard"]
        DASH["React + TS<br/>(TanStack Query, polls ~1.5s)"]
    end

    V -- "POST /telemetry (1 Hz, bursty)" --> API
    V -- "POST /vehicles/{id}/status (fault)" --> API
    API -- "SQL (txns, row locks, MVCC)" --> DB
    SWEEP -- "detect silent vehicles" --> DB
    DASH -- "GET /vehicles /fleet/state /zones/counts /anomalies" --> API
    API --> DOCS
```

**Notes.**
- Vertical slices inside the API: `telemetry · vehicles · zones · anomalies · fleet`.
- Ingestion absorbs bursts via the async connection pool; correctness under concurrency is enforced
  in the database (see [`../concurrency-and-isolation.md`](../concurrency-and-isolation.md)).
- The staleness sweep is the only thing that can detect *absence* of telemetry (offline vehicles).
- The dashboard holds no business logic; it validates responses with zod at the boundary.
