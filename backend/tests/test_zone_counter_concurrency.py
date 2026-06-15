import asyncio
from datetime import datetime, timezone

T0 = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc).isoformat()


def evt(vid, zone):
    return dict(vehicle_id=vid, ts=T0, lat=37.0, lon=-122.0, battery_pct=80,
                speed_mps=1.0, status="moving", error_codes=[], zone_entered=zone)


async def test_concurrent_same_zone_entries_all_counted(client):
    n = 50
    zone = "charging_bay_1"
    await asyncio.gather(*[client.post("/telemetry", json=evt(f"v-{i % 50 + 1}", zone)) for i in range(n)])
    r = await client.get("/zones/counts")
    counts = {z["zone_id"]: z["entry_count"] for z in r.json()["zones"]}
    assert counts[zone] == n
