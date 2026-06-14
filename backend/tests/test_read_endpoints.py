from datetime import datetime, timezone

from app.features.anomalies.staleness import sweep_once

T0 = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc).isoformat()


def evt(vid, **kw):
    base = dict(vehicle_id=vid, ts=T0, lat=37.0, lon=-122.0, battery_pct=80,
                speed_mps=1.0, status="moving", error_codes=[], zone_entered=None)
    base.update(kw)
    return base


async def test_fleet_state_counts(client, pool):
    await client.post("/vehicles/v-1/status", json={"status": "charging"})
    r = await client.get("/fleet/state")
    body = r.json()
    assert body["total"] == 50
    assert body["counts"]["charging"] >= 1


async def test_anomalies_filtered_by_vehicle(client):
    await client.post("/telemetry", json=evt("v-2", battery_pct=3))
    r = await client.get("/anomalies", params={"vehicle_id": "v-2"})
    body = r.json()
    assert body["count"] >= 1
    assert all(a["vehicle_id"] == "v-2" for a in body["anomalies"])


async def test_staleness_sweep_marks_offline(client, pool):
    await pool.execute("UPDATE vehicles SET last_seen_at = now() - interval '60 seconds' WHERE id='v-9'")
    await sweep_once()
    v = await pool.fetchrow("SELECT is_offline FROM vehicles WHERE id='v-9'")
    assert v["is_offline"] is True
    n = await pool.fetchval("SELECT count(*) FROM anomalies WHERE vehicle_id='v-9' AND type='stale_offline'")
    assert n == 1
