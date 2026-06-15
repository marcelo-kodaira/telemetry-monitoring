from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt

from app.core.config import settings
from app.core.domain import AnomalyType, Severity, VehicleStatus
from app.features.telemetry.schemas import TelemetryEvent

_EARTH_M = 6_371_000.0


@dataclass
class Anomaly:
    type: AnomalyType
    severity: Severity
    details: dict = field(default_factory=dict)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * _EARTH_M * asin(sqrt(a))


def evaluate(prev: dict | None, e: TelemetryEvent) -> list[Anomaly]:
    out: list[Anomaly] = []

    # --- instantaneous thresholds ---
    if e.battery_pct <= settings.battery_critical_pct:
        out.append(Anomaly(AnomalyType.CRITICAL_BATTERY, Severity.CRITICAL, {"battery_pct": e.battery_pct}))
    elif e.battery_pct <= settings.battery_low_pct:
        out.append(Anomaly(AnomalyType.LOW_BATTERY, Severity.WARNING, {"battery_pct": e.battery_pct}))
    if e.status == VehicleStatus.FAULT:
        out.append(Anomaly(AnomalyType.FAULT_STATUS, Severity.CRITICAL, {}))
    if e.error_codes:
        out.append(Anomaly(AnomalyType.ERROR_CODE_PRESENT, Severity.WARNING, {"error_codes": e.error_codes}))
    if e.speed_mps > settings.overspeed_mps:
        out.append(Anomaly(AnomalyType.OVERSPEED, Severity.WARNING, {"speed_mps": e.speed_mps}))
    if e.speed_mps > 0 and e.status in (VehicleStatus.IDLE, VehicleStatus.CHARGING):
        out.append(Anomaly(AnomalyType.STATE_INCONSISTENT, Severity.WARNING, {"speed_mps": e.speed_mps}))

    # --- stateful (need previous snapshot) ---
    if prev is not None and prev.get("last_timestamp") is not None:
        dt = (e.ts - prev["last_timestamp"]).total_seconds()
        if dt > 0:
            if prev.get("lat") is not None and prev.get("lon") is not None:
                implied = _haversine_m(prev["lat"], prev["lon"], e.lat, e.lon) / dt
                if implied > settings.teleport_mps:
                    out.append(Anomaly(AnomalyType.POSITION_JUMP, Severity.CRITICAL, {"implied_mps": round(implied, 2)}))
            drain = (prev["battery_pct"] - e.battery_pct) / dt
            if drain > settings.battery_drain_pct_per_s:
                out.append(Anomaly(AnomalyType.BATTERY_DRAIN, Severity.WARNING, {"drain_pct_per_s": round(drain, 2)}))
    if (
        e.status == VehicleStatus.CHARGING
        and prev is not None
        and prev.get("battery_pct") is not None
        and e.battery_pct < prev["battery_pct"]
    ):
        out.append(Anomaly(AnomalyType.CHARGING_NO_GAIN, Severity.WARNING, {}))

    return out
