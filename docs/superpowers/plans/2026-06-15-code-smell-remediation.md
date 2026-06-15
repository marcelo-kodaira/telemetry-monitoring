# Code-Smell Remediation Plan

**Source:** a 5-lens code-smell sweep (backend architecture/coupling, SQL & data layer, backend
quality, frontend/FSD, cross-cutting readability) produced **41 findings** (7 high, 12 medium, 22
low). Many overlap — deduped here into **8 themes** ordered by impact on readability/maintainability.

**Guiding principles for the sweep**
- **Behaviour-preserving.** Every change keeps the public behaviour identical. The 17 backend tests
  and 3 Playwright e2e tests are the safety net — run them after each theme; they must stay green.
- **Respect the ADR.** Raw SQL, vertical slices, READ COMMITTED + targeted locks, polling, no auth,
  `schema.sql` seeding — all deliberate, none "fixed."
- **One source of truth.** The dominant smell is duplicated domain vocabulary with no canonical
  definition; most high-severity items are facets of that.
- **Commit per theme** so each is reviewable and revertible.

---

## P1 — High impact

### Theme 1 — One source of truth for domain vocabulary
*Covers 6 findings (status ×4 sites, anomaly types, severity, mission/maintenance states).*

**Problem.** The status set `idle|moving|charging|fault` is hand-written in ≥4 places
(`telemetry/schemas.py`, `vehicles/schemas.py`, the `fleet/router.py` counts dict, the frontend zod
enum). Anomaly `type` (10 values) and `severity` (`critical|warning`) are bare literals scattered
across `anomaly_rules.py`, `staleness.py` (inside a SQL string), `ingest.py`, and the tests.
Mission/maintenance states (`active|cancelled|open|resolved`) likewise. A rename means editing
files that share nothing; miss one and the fleet aggregate silently drops a status.

**Fix.**
- New `backend/app/core/domain.py` with `StrEnum`s: `VehicleStatus`, `AnomalyType`, `Severity`,
  `MissionStatus`, `MaintenanceStatus` (StrEnum so they compare/serialize as the existing strings —
  zero behaviour change, zero SQL change).
- `telemetry/schemas.py` and `vehicles/schemas.py` import one `VehicleStatus` (delete the duplicated
  `Status = Literal[...]`).
- `fleet/router.py` builds the counts skeleton from the enum: `{s: 0 for s in VehicleStatus}`.
- `anomaly_rules.py` and `staleness.py` reference `AnomalyType.*` / `Severity.*`.
- Frontend: tighten `vehicle.schema.ts` `severity` to `z.enum(["critical","warning"])`; keep the
  status `z.enum` as the single frontend definition (note: generating FE types from the OpenAPI
  schema is the real long-term fix — listed as deferred).

**Files:** `core/domain.py` (new), `telemetry/schemas.py`, `vehicles/schemas.py`, `anomaly_rules.py`,
`staleness.py`, `ingest.py`, `fleet/router.py`, `frontend/.../vehicle.schema.ts`. **Effort:** M.
**Verify:** full backend suite (the StrEnum values must equal the old strings) + e2e.

### Theme 2 — Honest asyncpg result & jsonb handling
*Covers: jsonb json.dumps/loads (high); mission_cancelled command-tag parsing (high+medium); apply_fault round-trips (low).*

**Problem.** `anomalies.details` is `json.dumps`-encoded in `ingest.py` and `json.loads`-decoded in
`anomalies/router.py` — an implicit contract split across modules. `mission_cancelled` is derived
from `cancelled_tag.endswith(" 1")` — parsing the driver's command-tag text, which conflates 0-vs-many
and conveys no intent. `apply_fault` also does extra re-`SELECT`s where `RETURNING` would do.

**Fix.**
- Register a jsonb codec once in `db.py` `init_pool` (`set_type_codec('jsonb', json.dumps, json.loads)`);
  pass `a.details` as a dict on insert, read `r["details"]` as a dict — delete the `json.dumps` and
  `json.loads`.
- Cancel the mission with `UPDATE missions … RETURNING id` and set `mission_cancelled = (row is not
  None)`.
- Fold the maintenance insert to return its id without the fallback `SELECT` where clean.

**Files:** `core/db.py`, `telemetry/ingest.py`, `anomalies/router.py`, `vehicles/status_update.py`.
**Effort:** M. **Verify:** `test_fault_transition.py`, `test_read_endpoints.py`, `test_ingest.py`.

### Theme 3 — Logging & error visibility
*Covers 3 findings (staleness sweep `except: pass`, post_batch swallow, simulate swallow; zero logging).*

**Problem.** The staleness loop catches everything and `pass`es with no log — a persistent failure
silently stops offline-detection. `post_batch` and `simulate.py` swallow errors too. The ADR
commits to "basic structured logging"; there is none, least of all where errors are suppressed.

**Fix.** A module-level `logging.getLogger(__name__)` per module; `logger.exception(...)` in the
sweep's `except`; log (don't just stringify) unexpected errors in `post_batch`; log in `simulate.py`.
Configure a basic handler in `main.py` lifespan. Keep catch-and-continue resilience.

**Files:** `anomalies/staleness.py`, `telemetry/router.py`, `simulate.py`, `main.py`. **Effort:** S.
**Verify:** suite stays green; manually confirm a forced sweep error logs.

### Theme 4 — Kill the frontend↔backend threshold drift
*Covers 1 high finding (battery thresholds hardcoded on FE).*

**Problem.** `battery.ts` hardcodes `pct <= 5` / `pct <= 15` — the exact backend
`battery_critical_pct`/`battery_low_pct`. Tune the backend and the dashboard colouring silently
disagrees with the anomalies actually emitted, with nothing to catch it.

**Fix.** Extract named constants `BATTERY_CRITICAL_PCT` / `BATTERY_LOW_PCT` in
`frontend/src/shared/config` with a comment pointing at the backend setting, and reference them in
`batteryTone`. (Stretch, noted as optional: colour by `latest_anomaly` severity so the UI reflects
what the backend decided, removing the duplicated thresholds entirely.)

**Files:** `frontend/src/shared/config/index.ts`, `frontend/src/entities/vehicle/lib/battery.ts`.
**Effort:** S. **Verify:** e2e + screenshot.

---

## P2 — Medium impact

### Theme 5 — Make `ingest_event` and its SQL readable
*Covers: ingest SRP (high); SQL concatenated fragments (medium); telemetry column list duplicated ×3 (medium).*

**Problem.** `ingest_event` inserts, detects, persists anomalies, counts zones, upserts the snapshot,
and delegates faults in one function; its SQL is built from Python string fragments split mid-statement
(a missing space = malformed SQL), inconsistent with the triple-quoted `_SQL`/`_STMT` style already
used in `list_vehicles.py`/`staleness.py`. The vehicle column set is written three times.

**Fix.** Move each statement to a module-level triple-quoted SQL constant. Extract small helpers
(`_persist_anomalies`, `_bump_zone_counter`, `_upsert_snapshot`) so `ingest_event` reads as a short
orchestration. Define the snapshot column order once.

**Files:** `telemetry/ingest.py`. **Effort:** M. **Verify:** `test_ingest.py`, `test_zone_counter_concurrency.py`.

### Theme 6 — Uniform, typed API responses
*Covers: inconsistent response typing (medium ×2); get_vehicles annotation mismatch (medium); list_vehicles hand-mapping (low).*

**Problem.** `vehicles`/`telemetry` use Pydantic response models; `fleet`, `zones`, `anomalies`
return ad-hoc untyped dicts — absent from the OpenAPI/Scalar contract. `get_vehicles` annotates
`-> list[dict]` while declaring `response_model=list[VehicleView]` (the two disagree). `list_vehicles`
hand-builds dicts, repeating field names a third time.

**Fix.** Add `FleetStateView`, `ZoneCountsView`, `AnomalyListView` (+ item models) and annotate every
handler — one convention across all five routers. Fix `get_vehicles` to `-> list[VehicleView]`. Let
`response_model` shape `list_vehicles` (construct `VehicleView`/`LatestAnomaly` instead of dicts).

**Files:** `fleet/router.py`, `zones/router.py`, `anomalies/router.py`, `vehicles/router.py`,
`vehicles/list_vehicles.py`, new `schemas.py` where needed. **Effort:** M. **Verify:** suite + e2e +
check `/openapi.json` now lists all response schemas.

### Theme 7 — Frontend FSD & component hygiene
*Covers: missing barrels (medium); duplicated progress bar (medium); inconsistent loading/error (medium); query-key magic strings (low); Badge cva unused (low); cn() bypass (low ×2); statusTone typing + battery.ts misnamed (low); hardcoded poll label (low).*

**Fix (bundled).**
- Add per-slice public-API `index.ts` barrels; import slice roots, not deep files.
- Extract a shared `ProgressBar` into `shared/ui`; use it in `vehicle-card` and `zone-counters`.
- Standardize loading/error: give `usePolledQuery` consumers a consistent error render (or a small
  wrapper) so an outage isn't a blank panel.
- `queryKeys` registry co-located with each fetcher.
- Decide the `Badge` story: make status real cva variants (drop `statusTone`) **or** drop cva — one
  way. Type `statusTone`/status via the FE `VehicleStatus`.
- Use `cn()` for conditional classes in `vehicle-card`.
- Rename `battery.ts` (it also holds `statusTone`) → split into `battery.ts` + `status.ts`, or
  `vehicle-display.ts`.
- Derive the dashboard "polling every Ns" label from `POLL_INTERVAL_MS`.

**Files:** across `frontend/src/{entities,widgets,shared,pages}`. **Effort:** M. **Verify:** `npm run build`, e2e, screenshot.

---

## P3 — Low / quick wins (dead code & drift)

### Theme 8 — Remove cruft and latent drift
*Covers: vehicle_count dead config (low ×2); IngestResult.accepted dead field (low); unused FE assets (low ×2); zone list duplicated (low ×2); empty slice `__init__` / no public API (low); misleading "circular dependency" local import; inconsistent stateful-guard; dynamic-WHERE bookkeeping; mixed DB-access convention (low).*

**Fix.**
- Delete `settings.vehicle_count` (unused; the real seed is `schema.sql`).
- Drop `IngestResult.accepted` (always `True`; 202 already signals acceptance). Keep it on `BatchItemResult`.
- Delete `frontend/src/assets/` (unused scaffolding).
- Bind the zone list: seed `zone_counts` from the Python `ZONES` constant at startup **or** add a
  startup assertion that the DB zone set equals `ZONE_SET` (so drift fails loudly). Prefer seeding
  from `ZONES` so `schema.sql` stops duplicating the list.
- Give the `vehicles` slice a public `__init__` (`apply_fault`, `apply_status`) and move the
  `ingest.py` `apply_fault` import to module level — there is **no real cycle** (vehicles never
  imports telemetry), so the "avoid circular dependency" comment is misleading.
- Make the two stateful-rule prior-state guards consistent (`charging_no_gain` should use the same
  explicit `prev is not None` form as the haversine/drain block).
- Small `_param()` helper for the anomalies dynamic WHERE to remove manual `$N` bookkeeping.
- Fold the `post_status` existence check into the write path (`apply_status` returns/raises
  not-found) to remove the TOCTOU gap and an extra round-trip; standardize read endpoints on one
  DB-access helper.

**Files:** `core/config.py`, `telemetry/schemas.py`, `frontend/src/assets/*`, `core/zones.py` +
`db.py`/`main.py` (seeding), `features/*/__init__.py`, `anomaly_rules.py`, `anomalies/router.py`,
`vehicles/router.py` + `status_update.py`. **Effort:** S–M. **Verify:** full suite + e2e.

---

## Deferred (out of scope for this sweep)
- Generating the frontend types/enums from the backend OpenAPI schema (the proper end-state for
  Theme 1's cross-stack duplication) — meaningful tooling change; note it, don't build it now.
- Structured/JSON logging with correlation ids and a metrics/tracing stack (ADR Q4 explicitly
  defers observability beyond basic logging).

## Sequencing
1, 2, 3, 4 (P1) → 5, 6, 7 (P2) → 8 (P3). Run `pytest` after each backend theme and `npm run build`
+ `npx playwright test` after each frontend theme; commit per theme. Total ≈ a focused half-day.
