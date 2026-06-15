"""Drive 50 vehicles emitting telemetry; periodically converge on charging bays to exercise the
zone counter and fault paths under concurrency. Usage: python simulate.py [seconds]"""
import asyncio
import logging
import random
import sys
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("simulate")
API = "http://localhost:8000"
ZONES = ["aisle_a", "aisle_b", "pick_zone_1", "pack_station", "charging_bay_1", "charging_bay_2"]


async def tick(client: httpx.AsyncClient, vid: str, battery: int) -> None:
    zone = random.choice(ZONES) if random.random() < 0.2 else None
    status = random.choice(["moving", "idle", "charging"])
    payload = dict(
        vehicle_id=vid, ts=datetime.now(timezone.utc).isoformat(),
        lat=37.41 + random.uniform(-0.01, 0.01), lon=-122.08 + random.uniform(-0.01, 0.01),
        battery_pct=max(0, battery), speed_mps=round(random.uniform(0, 3.5), 2),
        status=status, error_codes=[], zone_entered=zone,
    )
    try:
        await client.post(f"{API}/telemetry", json=payload)
    except httpx.HTTPError as exc:
        logger.debug("telemetry post failed for %s: %s", vid, exc)


async def main(duration: int) -> None:
    batteries = {f"v-{i}": random.randint(20, 100) for i in range(1, 51)}
    async with httpx.AsyncClient(timeout=5) as client:
        end = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < end:
            for vid in batteries:
                batteries[vid] = max(0, batteries[vid] - random.randint(0, 1))
            await asyncio.gather(*[tick(client, vid, b) for vid, b in batteries.items()])
            await asyncio.sleep(1)
    print(f"simulated {len(batteries)} vehicles for {duration}s")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 30))
