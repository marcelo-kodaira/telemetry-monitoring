from datetime import datetime, timezone

T0 = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc).isoformat()


def evt(**kw):
    base = dict(vehicle_id="v-1", ts=T0, lat=37.0, lon=-122.0, battery_pct=80,
                speed_mps=1.0, status="moving", error_codes=[], zone_entered=None)
    base.update(kw)
    return base


async def test_ingest_accepts_and_updates_snapshot(client, pool):
    r = await client.post("/telemetry", json=evt(battery_pct=12))
    assert r.status_code == 202
    body = r.json()
    assert body["accepted"] is True
    assert any(a["type"] == "low_battery" for a in body["detected_anomalies"])
    v = await pool.fetchrow("SELECT status, battery_pct FROM vehicles WHERE id='v-1'")
    assert v["battery_pct"] == 12


async def test_unknown_zone_rejected(client):
    r = await client.post("/telemetry", json=evt(zone_entered="not_a_zone"))
    assert r.status_code == 422


async def test_zone_entry_increments_counter(client, pool):
    await client.post("/telemetry", json=evt(zone_entered="aisle_a"))
    c = await pool.fetchval("SELECT entry_count FROM zone_counts WHERE zone_id='aisle_a'")
    assert c == 1


async def test_anomaly_is_edge_triggered(client, pool):
    await client.post("/telemetry", json=evt(battery_pct=12))
    await client.post("/telemetry", json=evt(battery_pct=11, ts="2026-06-14T12:00:01Z"))
    n = await pool.fetchval(
        "SELECT count(*) FROM anomalies WHERE vehicle_id='v-1' AND type='low_battery'"
    )
    assert n == 1
