# Running Locally

A precise, end-to-end guide to run the service, the dashboard, and the test suites. Every command
below was run against this repo; the expected output is what you should actually see.

> Verified on: Docker 28 (with Compose v2), Node.js 22, Python 3.12, Linux/WSL2. Anything matching
> the prerequisite versions below should behave identically.

## 1. Prerequisites

| Tool | Minimum | Used for | Check |
| ---- | ------- | -------- | ----- |
| Docker + Compose v2 | Docker 24+, `docker compose` (not `docker-compose`) | Postgres + the API | `docker --version && docker compose version` |
| Node.js | 18+ (20/22 fine) | the dashboard + Playwright e2e | `node --version` |
| Python | 3.12 | *only* if you run the backend outside Docker | `python3 --version` |

The Docker daemon must be running (`docker info` succeeds). All commands are run **from the repository
root** unless stated otherwise.

## 2. Start the backend (Postgres + API) — one command

```bash
docker compose up -d --build
```

This builds the API image, starts PostgreSQL 16, and starts the API. The schema is created and seeded
(20 zones, 50 vehicles `v-1…v-50`, 50 active missions) automatically on first boot. Wait a few seconds,
then confirm:

```bash
curl -s localhost:8000/health
# -> {"status":"ok"}

curl -s localhost:8000/fleet/state
# -> {"generated_at":"...","total":50,"offline":...,"counts":{"idle":50,"moving":0,"charging":0,"fault":0}}
```

- **API:** http://localhost:8000
- **Interactive API docs (Scalar):** http://localhost:8000/scalar
- **OpenAPI schema:** http://localhost:8000/openapi.json
- **Postgres:** `localhost:5432` (user/password/db all `fleet`)

Watch logs with `docker compose logs -f api`.

## 3. Start the dashboard

The frontend is not containerized — run it with npm (it talks to the API at `http://localhost:8000`):

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. With no live data the 50 vehicles show as idle at 100% and go
`offline` after ~10 s of silence (the staleness sweep doing its job). For a lively dashboard, run the
simulator (next section).

## 4. Feed live data (optional)

Drive all 50 vehicles for 120 seconds (runs inside the API container, so no local Python needed):

```bash
docker compose exec api python simulate.py 120
```

Statuses, batteries, anomalies, and zone counts will start moving on the dashboard.

## 5. Run the tests

**Backend — 17 tests against a real Postgres (the two concurrency proofs included):**

```bash
docker compose exec api pytest -q
# -> 17 passed
```

The graded guarantees are pinned here: `test_zone_counter_concurrency` (50 concurrent same-zone entries
→ count exactly 50) and `test_fault_transition` (20 racing faults → exactly one maintenance record).

**Frontend — 4 Playwright e2e tests against the running stack** (needs §2 up; Playwright starts the
dashboard itself):

```bash
cd frontend
npx playwright install chromium   # first time only — downloads the browser
npx playwright test
# -> 4 passed
```

The 4th test aborts the API and asserts the dashboard's error state and the connection toast appear.

## 6. Stop everything

```bash
docker compose down            # stop API + Postgres (keeps no volumes — data is ephemeral)
# Ctrl-C in the `npm run dev` terminal stops the dashboard.
```

## 7. Alternative: run the backend without Docker

Useful for backend development with auto-reload. Keep Postgres in Docker:

```bash
docker compose up -d db        # just Postgres on localhost:5432

cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload     # API on http://localhost:8000
```

Run the backend tests locally the same way (Postgres must be up):

```bash
cd backend && .venv/bin/pytest -q     # -> 17 passed
```

The default `DATABASE_URL` (`postgresql://fleet:fleet@localhost:5432/fleet`) already matches the
Docker Postgres; override it via env var or `backend/.env` if needed.

## 8. Troubleshooting

- **`port is already allocated` (5432 or 8000):** something else is using the port. Find and stop it
  (`docker ps`, then `docker rm -f <name>`), or stop a local Postgres/uvicorn. Re-run `docker compose up -d`.
- **Dashboard shows a red "Lost connection" toast and "Couldn't load…" panels:** the API isn't
  reachable. Confirm `curl localhost:8000/health` returns ok and that `VITE_API_URL` (in `frontend/.env`,
  default `http://localhost:8000`) points at it.
- **Want a clean slate without rebuilding:** reset the seeded data in place —
  ```bash
  docker compose exec db psql -U fleet -d fleet -c "TRUNCATE telemetry, anomalies, maintenance RESTART IDENTITY; UPDATE zone_counts SET entry_count=0; UPDATE vehicles SET status='idle', battery_pct=100, is_offline=false, last_timestamp=NULL, active_anomaly_types='{}';"
  ```
- **Playwright can't find a browser:** run `npx playwright install chromium` once.
- **Rebuild after backend changes:** `docker compose up -d --build` (the image isn't layer-cached on
  source changes by design — it copies the source before installing).
