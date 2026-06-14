import asyncio


async def test_concurrent_duplicate_faults_create_one_maintenance(client, pool):
    vid = "v-7"
    payload = {"status": "fault", "reason": "smoke"}
    await asyncio.gather(*[client.post(f"/vehicles/{vid}/status", json=payload) for _ in range(20)])

    open_rows = await pool.fetch("SELECT id FROM maintenance WHERE vehicle_id=$1 AND status='open'", vid)
    assert len(open_rows) == 1

    cancelled = await pool.fetch("SELECT id FROM missions WHERE vehicle_id=$1 AND status='cancelled'", vid)
    assert len(cancelled) == 1

    v = await pool.fetchrow("SELECT status FROM vehicles WHERE id=$1", vid)
    assert v["status"] == "fault"


async def test_non_fault_status_is_fast_path(client, pool):
    r = await client.post("/vehicles/v-3/status", json={"status": "charging"})
    assert r.status_code == 200
    v = await pool.fetchrow("SELECT status FROM vehicles WHERE id='v-3'")
    assert v["status"] == "charging"


async def test_status_update_unknown_vehicle_404(client):
    r = await client.post("/vehicles/nope/status", json={"status": "idle"})
    assert r.status_code == 404
