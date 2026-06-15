from collections.abc import Callable
from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt

from app.core.config import settings
from app.core.domain import AnomalyType, Severity, VehicleStatus
from app.features.telemetry.schemas import TelemetryEvent

EARTH_RADIUS_M = 6_371_000.0
RATE_DECIMALS = 2  # rounding for reported implied-speed / drain-rate values


@dataclass
class Anomaly:
    type: AnomalyType
    severity: Severity
    details: dict = field(default_factory=dict)


@dataclass
class RuleContext:
    """Everything a rule needs: the incoming event and (optionally) the previous snapshot.
    Derived values are computed once here so each rule stays a flat, single-condition check."""

    event: TelemetryEvent
    previous: dict | None

    @property
    def seconds_since_previous(self) -> float | None:
        if self.previous is None or self.previous.get("last_timestamp") is None:
            return None
        elapsed = (self.event.ts - self.previous["last_timestamp"]).total_seconds()
        return elapsed if elapsed > 0 else None

    @property
    def has_previous_position(self) -> bool:
        return self.previous is not None and self.previous.get("lat") is not None and self.previous.get("lon") is not None


Rule = Callable[[RuleContext], Anomaly | None]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    delta_lat, delta_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(delta_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


# --- instantaneous threshold rules (critical/low battery are mutually exclusive by construction) ---
def _critical_battery(ctx: RuleContext) -> Anomaly | None:
    if ctx.event.battery_pct <= settings.battery_critical_pct:
        return Anomaly(AnomalyType.CRITICAL_BATTERY, Severity.CRITICAL, {"battery_pct": ctx.event.battery_pct})
    return None


def _low_battery(ctx: RuleContext) -> Anomaly | None:
    if settings.battery_critical_pct < ctx.event.battery_pct <= settings.battery_low_pct:
        return Anomaly(AnomalyType.LOW_BATTERY, Severity.WARNING, {"battery_pct": ctx.event.battery_pct})
    return None


def _fault_status(ctx: RuleContext) -> Anomaly | None:
    if ctx.event.status == VehicleStatus.FAULT:
        return Anomaly(AnomalyType.FAULT_STATUS, Severity.CRITICAL)
    return None


def _error_codes_present(ctx: RuleContext) -> Anomaly | None:
    if ctx.event.error_codes:
        return Anomaly(AnomalyType.ERROR_CODE_PRESENT, Severity.WARNING, {"error_codes": ctx.event.error_codes})
    return None


def _overspeed(ctx: RuleContext) -> Anomaly | None:
    if ctx.event.speed_mps > settings.overspeed_mps:
        return Anomaly(AnomalyType.OVERSPEED, Severity.WARNING, {"speed_mps": ctx.event.speed_mps})
    return None


def _moving_while_stationary_status(ctx: RuleContext) -> Anomaly | None:
    if ctx.event.speed_mps > 0 and ctx.event.status in (VehicleStatus.IDLE, VehicleStatus.CHARGING):
        return Anomaly(AnomalyType.STATE_INCONSISTENT, Severity.WARNING, {"speed_mps": ctx.event.speed_mps})
    return None


# --- stateful rules (need the previous snapshot; guard then compute, no nesting) ---
def _position_jump(ctx: RuleContext) -> Anomaly | None:
    elapsed = ctx.seconds_since_previous
    if elapsed is None or not ctx.has_previous_position:
        return None
    implied_mps = _haversine_m(ctx.previous["lat"], ctx.previous["lon"], ctx.event.lat, ctx.event.lon) / elapsed
    if implied_mps <= settings.teleport_mps:
        return None
    return Anomaly(AnomalyType.POSITION_JUMP, Severity.CRITICAL, {"implied_mps": round(implied_mps, RATE_DECIMALS)})


def _battery_drain(ctx: RuleContext) -> Anomaly | None:
    elapsed = ctx.seconds_since_previous
    if elapsed is None:
        return None
    drain_rate = (ctx.previous["battery_pct"] - ctx.event.battery_pct) / elapsed
    if drain_rate <= settings.battery_drain_pct_per_s:
        return None
    return Anomaly(AnomalyType.BATTERY_DRAIN, Severity.WARNING, {"drain_pct_per_s": round(drain_rate, RATE_DECIMALS)})


def _charging_without_gain(ctx: RuleContext) -> Anomaly | None:
    if ctx.event.status != VehicleStatus.CHARGING or ctx.previous is None:
        return None
    previous_battery = ctx.previous.get("battery_pct")
    if previous_battery is None or ctx.event.battery_pct >= previous_battery:
        return None
    return Anomaly(AnomalyType.CHARGING_NO_GAIN, Severity.WARNING)


RULES: list[Rule] = [
    _critical_battery,
    _low_battery,
    _fault_status,
    _error_codes_present,
    _overspeed,
    _moving_while_stationary_status,
    _position_jump,
    _battery_drain,
    _charging_without_gain,
]


def evaluate(previous: dict | None, event: TelemetryEvent) -> list[Anomaly]:
    ctx = RuleContext(event=event, previous=previous)
    return [anomaly for rule in RULES if (anomaly := rule(ctx)) is not None]
