"""Drive the fleet emitting telemetry; vehicles periodically converge on charging bays to exercise
the zone counter and fault paths under concurrency. Usage: python simulate.py [seconds]"""
import asyncio
import logging
import random
import sys
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("simulate")

API_URL = "http://localhost:8000"
FLEET_SIZE = 50
TICK_SECONDS = 1.0
DEFAULT_DURATION_SECONDS = 30

ZONE_ENTRY_PROBABILITY = 0.2
VISITED_ZONES = ["aisle_a", "aisle_b", "pick_zone_1", "pack_station", "charging_bay_1", "charging_bay_2"]
STATUSES = ["moving", "idle", "charging"]
MAX_SPEED_MPS = 3.5
BASE_LAT, BASE_LON = 37.41, -122.08
POSITION_JITTER_DEG = 0.01
INITIAL_BATTERY_RANGE = (20, 100)
MAX_DRAIN_PER_TICK = 1


async def send_tick(client: httpx.AsyncClient, vehicle_id: str, battery_pct: int) -> None:
    zone_entered = random.choice(VISITED_ZONES) if random.random() < ZONE_ENTRY_PROBABILITY else None
    payload = dict(
        vehicle_id=vehicle_id,
        ts=datetime.now(timezone.utc).isoformat(),
        lat=BASE_LAT + random.uniform(-POSITION_JITTER_DEG, POSITION_JITTER_DEG),
        lon=BASE_LON + random.uniform(-POSITION_JITTER_DEG, POSITION_JITTER_DEG),
        battery_pct=max(0, battery_pct),
        speed_mps=round(random.uniform(0, MAX_SPEED_MPS), 2),
        status=random.choice(STATUSES),
        error_codes=[],
        zone_entered=zone_entered,
    )
    try:
        await client.post(f"{API_URL}/telemetry", json=payload)
    except httpx.HTTPError as exc:
        logger.debug("telemetry post failed for %s: %s", vehicle_id, exc)


async def main(duration_seconds: int) -> None:
    battery_by_vehicle = {
        f"v-{i}": random.randint(*INITIAL_BATTERY_RANGE) for i in range(1, FLEET_SIZE + 1)
    }
    async with httpx.AsyncClient(timeout=5) as client:
        deadline = asyncio.get_event_loop().time() + duration_seconds
        while asyncio.get_event_loop().time() < deadline:
            for vehicle_id in battery_by_vehicle:
                battery_by_vehicle[vehicle_id] = max(
                    0, battery_by_vehicle[vehicle_id] - random.randint(0, MAX_DRAIN_PER_TICK)
                )
            await asyncio.gather(
                *[send_tick(client, vehicle_id, battery) for vehicle_id, battery in battery_by_vehicle.items()]
            )
            await asyncio.sleep(TICK_SECONDS)
    logger.info("simulated %d vehicles for %ds", len(battery_by_vehicle), duration_seconds)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DURATION_SECONDS))
