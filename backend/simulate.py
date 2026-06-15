"""Simulate a fleet of autonomous vehicles with a coherent per-vehicle lifecycle, standing in for
the vehicles' edge clients. Each vehicle runs its own state machine:

    idle ──(starts a mission)──▶ moving ──(battery low)──▶ charging ──(recharged)──▶ idle

Statuses are *sticky* (a vehicle stays in a state until a real transition), speed and battery track
the status (no movement while idle/charging; battery drains while moving, recharges while charging),
position drifts plausibly, and `zone_entered` fires only on an actual crossing into a new zone — so
the dashboard tells a believable story instead of flickering randomly.

Faults are an operational event (raise them via POST /vehicles/{id}/status), not simulated here.
Usage: python simulate.py [seconds]
"""
import asyncio
import logging
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # silence per-request httpx noise
logger = logging.getLogger("simulate")

API_URL = "http://localhost:8000"
FLEET_SIZE = 50
TICK_SECONDS = 1.0
DEFAULT_DURATION_SECONDS = 30

WORK_ZONES = [
    "inbound_dock_a", "receiving_staging", "aisle_a", "aisle_b", "aisle_c",
    "pick_zone_1", "pick_zone_2", "pack_station", "sort_belt", "outbound_dock_a",
]
CHARGING_BAYS = ["charging_bay_1", "charging_bay_2", "charging_bay_3"]

MOVING_SPEED_RANGE = (0.6, 2.8)   # m/s, kept under the 3.0 policy limit
DRAIN_RANGE = (0.4, 1.4)          # %/tick while moving (under the 2 %/s drain alarm)
CHARGE_RANGE = (3.0, 5.0)         # %/tick while charging
P_START_MISSION = 0.10            # idle -> moving per tick
P_END_MISSION = 0.03              # moving -> idle per tick (mission ~lasts tens of seconds)
P_CROSS_WORK_ZONE = 0.12          # chance a moving vehicle crosses into a new work zone
RESUME_BATTERY = 95               # charging -> idle once recharged
BASE_LAT, BASE_LON = 37.41, -122.08


@dataclass
class Vehicle:
    id: str
    status: str
    battery: float
    lat: float
    lon: float
    speed: float = 0.0
    zone: str | None = None          # current zone, to detect crossings
    charge_at: int = field(default_factory=lambda: random.randint(10, 25))

    def _cross_into(self, zone: str) -> str | None:
        """Record a zone crossing; return the zone only if it's actually new."""
        if zone == self.zone:
            return None
        self.zone = zone
        return zone

    def step(self) -> str | None:
        """Advance one tick. Returns zone_entered if the vehicle just crossed into a new zone.

        Transitions are decided from the *current* state first; speed and battery effects are then
        applied to the *final* status, so a vehicle never reports e.g. idle-with-speed or
        charging-while-draining on a transition tick."""
        entered: str | None = None

        if self.status == "idle":
            if random.random() < P_START_MISSION:
                self.status = "moving"
        elif self.status == "moving":
            if self.battery <= self.charge_at:                # battery low -> head in to recharge
                self.status = "charging"
                self.charge_at = random.randint(10, 25)
                entered = self._cross_into(random.choice(CHARGING_BAYS))
            elif random.random() < P_END_MISSION:             # mission complete
                self.status = "idle"
        elif self.status == "charging":
            if self.battery >= RESUME_BATTERY:                # recharged
                self.status = "idle"
                self.zone = None

        if self.status == "moving":
            self.speed = round(random.uniform(*MOVING_SPEED_RANGE), 2)
            self.battery = max(0.0, self.battery - random.uniform(*DRAIN_RANGE))
            self._wander()
            if entered is None and random.random() < P_CROSS_WORK_ZONE:
                entered = self._cross_into(random.choice(WORK_ZONES))
        else:  # idle or charging -> stationary
            self.speed = 0.0
            if self.status == "charging":
                self.battery = min(100.0, self.battery + random.uniform(*CHARGE_RANGE))

        return entered

    def _wander(self) -> None:
        # drift no further than the vehicle could actually travel this tick, so the implied speed
        # (haversine / dt) stays well under the teleport threshold
        deg = (self.speed * TICK_SECONDS) / 111_320.0
        self.lat += random.uniform(-deg, deg)
        self.lon += random.uniform(-deg, deg)


def build_fleet() -> list[Vehicle]:
    fleet: list[Vehicle] = []
    for i in range(1, FLEET_SIZE + 1):
        status = random.choice(["idle", "moving"])  # a fleet starts working, not pre-charging
        fleet.append(
            Vehicle(
                id=f"v-{i}",
                status=status,
                battery=random.uniform(40, 100),
                lat=BASE_LAT + random.uniform(-0.01, 0.01),
                lon=BASE_LON + random.uniform(-0.01, 0.01),
                speed=round(random.uniform(*MOVING_SPEED_RANGE), 2) if status == "moving" else 0.0,
            )
        )
    return fleet


async def post(client: httpx.AsyncClient, vehicle: Vehicle, zone_entered: str | None) -> None:
    payload = dict(
        vehicle_id=vehicle.id,
        ts=datetime.now(timezone.utc).isoformat(),
        lat=round(vehicle.lat, 6),
        lon=round(vehicle.lon, 6),
        battery_pct=int(vehicle.battery),
        speed_mps=vehicle.speed,
        status=vehicle.status,
        error_codes=[],
        zone_entered=zone_entered,
    )
    try:
        await client.post(f"{API_URL}/telemetry", json=payload)
    except httpx.HTTPError as exc:
        logger.debug("telemetry post failed for %s: %s", vehicle.id, exc)


async def main(duration_seconds: int) -> None:
    fleet = build_fleet()
    ticks = max(1, int(duration_seconds / TICK_SECONDS))
    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(ticks):
            crossings = [v.step() for v in fleet]
            await asyncio.gather(*[post(client, v, z) for v, z in zip(fleet, crossings)])
            await asyncio.sleep(TICK_SECONDS)
    logger.info("simulated %d vehicles for %ds", len(fleet), duration_seconds)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DURATION_SECONDS))
