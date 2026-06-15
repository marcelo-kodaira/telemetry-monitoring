# Fleet Telemetry Monitoring

A vertical slice of a fleet-monitoring system for 50 autonomous industrial vehicles emitting
telemetry at 1 Hz. It ingests telemetry under concurrent bursts, detects anomalies in real time,
counts zone traversals without loss under concurrency, handles `fault` transitions atomically, and
serves a live React dashboard.

This repository is also a demonstration of **AI-driven development**: the design, the Architecture
Decision Record, the diagrams, and the prompt-by-prompt AI log are first-class deliverables.

- **Start here:** [`docs/adr/0001-fleet-telemetry-architecture.md`](docs/adr/0001-fleet-telemetry-architecture.md) — the ADR (decisions, alternatives, the four required questions).
- **Concurrency reasoning:** [`docs/concurrency-and-isolation.md`](docs/concurrency-and-isolation.md)
- **API contract:** [`docs/api-contract.md`](docs/api-contract.md) · **Diagrams:** [`docs/diagrams/`](docs/diagrams/)
- **AI interaction log:** [`AI_INTERACTION_LOG.md`](AI_INTERACTION_LOG.md) · **AI-driven SDLC:** [`docs/ai-driven-sdlc.md`](docs/ai-driven-sdlc.md)

## Stack

FastAPI + asyncpg + raw SQL (vertical slices) · PostgreSQL 16 · Scalar API docs ·
React + TypeScript + Vite (Feature-Sliced Design) · shadcn-style UI · zod · TanStack Query (polling) ·
Playwright e2e. See the ADR for why each was chosen.

## Prerequisites

- Docker (with Compose v2) — for PostgreSQL and the API
- Node.js 18+ — for the dashboard
- Python 3.12 — only if you want to run the backend/tests outside Docker

## Run it (one path, ~3 commands)

> For a precise, verified walkthrough (tests, simulator, the no-Docker path, troubleshooting) see
> [`docs/running-locally.md`](docs/running-locally.md).

```bash
# 1. Start PostgreSQL + the API (schema is applied and seeded automatically on boot)
docker compose up -d --build          # API on http://localhost:8000  (Scalar docs at /scalar)

# 2. Start the dashboard
cd frontend && npm install && npm run dev   # http://localhost:5173

# 3. (optional) Feed live data — drives all 50 vehicles for 120s
docker compose exec api python simulate.py 120
```

Open **http://localhost:5173** for the dashboard and **http://localhost:8000/scalar** for the API
reference. The dashboard polls every 1.5s and shows per-status totals, the 50-vehicle grid (status +
battery + latest anomaly), and live per-zone entry counts.

### Running the backend without Docker (optional)

```bash
docker compose up -d db                # just Postgres
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload    # http://localhost:8000
```

## Tests

**Backend (17 tests, incl. the two concurrency proofs) — against real Postgres:**

```bash
docker compose exec api pytest -v
# or locally:  cd backend && .venv/bin/pytest -v
```

The two graded guarantees are pinned by tests:
- `test_zone_counter_concurrency.py` — 50 concurrent same-zone entries ⇒ count is exactly **50** (no lost updates).
- `test_fault_transition.py` — 20 racing duplicate faults ⇒ exactly **one** maintenance record + one mission cancelled.

**Frontend e2e (Playwright, 3 specs) — needs the API and dashboard running:**

```bash
cd frontend
npx playwright install chromium     # first time only
npx playwright test
```

## API summary

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/telemetry` · `/telemetry/batch` | ingest events (handles concurrent bursts) |
| POST | `/vehicles/{id}/status` | status update; `fault` → atomic mission cancel + maintenance |
| GET | `/zones/counts` | per-zone entry counts (live) |
| GET | `/fleet/state` | aggregate per-status counts (MVCC-safe) |
| GET | `/vehicles` | dashboard list with most-recent anomaly per vehicle |
| GET | `/anomalies?vehicle_id&start&end&limit` | recent anomalies by vehicle + time range |

Full request/response/error contract: [`docs/api-contract.md`](docs/api-contract.md). Live, browsable
contract: `/scalar`.

## Project layout

```
backend/    FastAPI app — app/core (pool, config, ZONES) + app/features/<slice>; schema.sql; tests/; simulate.py
frontend/   React + TS — src/{app,pages,widgets,entities,shared} (FSD); e2e/ (Playwright)
docs/       ADR, architecture, concurrency, API contract, diagrams, AI-driven SDLC
AI_INTERACTION_LOG.md   the prompt-by-prompt AI record
docs/superpowers/        the design spec and the backend/frontend implementation plans
```

## Notes & assumptions

The spec deliberately left things open; the key assumptions (timestamps, mission/maintenance shape,
vehicle seeding, anomaly thresholds, what "scale" means, what was left out) are documented in the
ADR's §5. Highlights: PostgreSQL is chosen so the isolation strategy is real and demonstrable;
anomalies are detected with a hybrid model (thresholds + stateful diffs + a background staleness
sweep) and persisted edge-triggered; the dashboard uses polling (justified over WebSockets for a
read-only 1 Hz feed).
