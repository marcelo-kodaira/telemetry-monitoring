# API Contract

The decided request/response/error contract for every endpoint. This is the source of truth that
FastAPI's OpenAPI schema and the **Scalar** UI (`/scalar`) render, and that the frontend's zod
schemas mirror. Timestamps are ISO-8601 UTC throughout.

> Status: design phase — this is the target contract the implementation must satisfy.

## Conventions

- **Content type:** `application/json`.
- **Validation errors:** FastAPI's `422` with `{ "detail": [...] }` for malformed bodies / params.
- **Unknown vehicle:** `404` (the 50 vehicles are seeded; an unknown id on a status update is a
  client error). Telemetry self-registers, so it does not 404 on unknown id.
- **Time params:** ISO-8601 UTC; ranges are half-open `[start, end)` (inclusive start, exclusive end).

## Endpoints

### `POST /telemetry` — ingest one event  · tag: `telemetry`

Request body (`TelemetryEvent`):

| field         | type                                   | notes                                            |
| ------------- | -------------------------------------- | ------------------------------------------------ |
| `vehicle_id`  | string                                 | e.g. `v-12`                                       |
| `ts`          | string (ISO-8601 UTC)                  | event time                                        |
| `lat`, `lon`  | number                                 | position (enables `position_jump` check)          |
| `battery_pct` | integer 0–100                          |                                                   |
| `speed_mps`   | number ≥ 0                             |                                                   |
| `status`      | enum `idle\|moving\|charging\|fault`   |                                                   |
| `error_codes` | string[]                               | may be empty                                      |
| `zone_entered`| string \| null                         | if non-null **must** be one of the 20 `ZONES`     |

Responses:
- `202 Accepted` → `{ "accepted": true, "detected_anomalies": [ { "type": "low_battery", "severity": "warning" } ] }`
- `422` → invalid body, unknown `status`, or `zone_entered` not in `ZONES`.

A `status: "fault"` event delegates to the same atomic fault command as `POST /vehicles/{id}/status`.

### `POST /telemetry/batch` — ingest many  · tag: `telemetry`

Body: `{ "events": TelemetryEvent[] }`. **Each event is processed in its own transaction**
(independent, best-effort): a malformed or stale event is skipped without aborting the rest.

Response `200`:
```json
{ "results": [
  { "vehicle_id": "v-1", "ts": "...", "accepted": true,  "detected_anomalies": [] },
  { "vehicle_id": "v-2", "ts": "...", "accepted": false, "error": "zone_entered not in ZONES" }
] }
```

### `POST /vehicles/{id}/status` — status update / fault handling  · tag: `vehicles`

Body: `{ "status": "idle|moving|charging|fault", "reason": "optional string" }`.

- **Fault (first time):** atomic transaction — set `fault`, cancel active mission, open maintenance.
  `200` → `{ "vehicle_id": "v-12", "status": "fault", "fault_handled": true, "maintenance_id": 42, "mission_cancelled": true }`
- **Fault (duplicate / idempotent):** no new record.
  `200` → `{ "vehicle_id": "v-12", "status": "fault", "fault_handled": false, "maintenance_id": 42, "mission_cancelled": false }`
- **Non-fault:** fast-path update → `200` → `{ "vehicle_id": "v-12", "status": "moving" }`
- `404` unknown vehicle · `422` invalid status.

### `GET /zones/counts` — per-zone entry counts  · tag: `zones`

`200` → `{ "generated_at": "...", "zones": [ { "zone_id": "charging_bay_1", "entry_count": 137 }, ... ] }`
(all 20 zones always present, including zeros).

### `GET /fleet/state` — aggregate fleet state  · tag: `fleet`

`200` →
```json
{ "generated_at": "...", "total": 50, "offline": 2,
  "counts": { "idle": 18, "moving": 24, "charging": 6, "fault": 2 } }
```
Backed by a single `GROUP BY` (MVCC snapshot — safe under concurrent updates).

### `GET /vehicles` — dashboard list  · tag: `vehicles`

`200` → `{ "vehicles": [ {
  "vehicle_id": "v-12", "status": "moving", "battery_pct": 77, "lat": 37.41, "lon": -122.08,
  "is_offline": false, "last_seen_at": "...",
  "latest_anomaly": { "type": "low_battery", "severity": "warning", "detected_at": "..." }
} ] }`

`latest_anomaly` is the per-vehicle most-recent via `DISTINCT ON (vehicle_id)`, or `null`.

### `GET /anomalies` — query recent anomalies  · tag: `anomalies`

Query params:

| param        | required | default | notes                                             |
| ------------ | -------- | ------- | ------------------------------------------------- |
| `vehicle_id` | no       | —       | filter to one vehicle                             |
| `start`      | no       | —       | ISO-8601 UTC; inclusive lower bound               |
| `end`        | no       | —       | ISO-8601 UTC; exclusive upper bound               |
| `limit`      | no       | `100`   | max `1000`                                         |

Ordering: `detected_at DESC`. With no `start`/`end`, returns the most recent `limit` anomalies (no
implicit time filter). Response `200` →
`{ "count": 2, "anomalies": [ { "id": 991, "vehicle_id": "v-12", "type": "low_battery", "severity": "warning", "detected_at": "...", "details": { "battery_pct": 14 } } ] }`

## Status-code summary

| Code | When |
| ---- | ---- |
| 200  | successful reads and status updates |
| 202  | telemetry accepted |
| 404  | status update for unknown (unseeded) vehicle |
| 422  | request/param validation failure (bad enum, unknown zone, bad time format) |

## Scalar / OpenAPI curation

`/scalar` renders a **curated** OpenAPI, not a raw auto-dump: each slice is a tag
(`telemetry`, `vehicles`, `zones`, `anomalies`, `fleet`); every operation has a summary and a
request/response example; the anomaly `type`/`severity` enums and the `status` enum are documented.
FastAPI also serves `/openapi.json` and the default `/docs` (Swagger) for convenience.
