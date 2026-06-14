from datetime import datetime, timedelta, timezone

from app.features.telemetry.anomaly_rules import evaluate
from app.features.telemetry.schemas import TelemetryEvent

T0 = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)


def ev(**kw):
    base = dict(vehicle_id="v-1", ts=T0, lat=37.0, lon=-122.0, battery_pct=80,
                speed_mps=1.0, status="moving", error_codes=[], zone_entered=None)
    base.update(kw)
    return TelemetryEvent(**base)


def types(prev, e):
    return {a.type for a in evaluate(prev, e)}


def test_low_and_critical_battery():
    assert "low_battery" in types(None, ev(battery_pct=14))
    assert "critical_battery" in types(None, ev(battery_pct=4))


def test_fault_status_and_error_codes():
    assert "fault_status" in types(None, ev(status="fault"))
    assert "error_code_present" in types(None, ev(error_codes=["E12"]))


def test_overspeed_and_state_inconsistency():
    assert "overspeed" in types(None, ev(speed_mps=3.5))
    assert "state_inconsistent" in types(None, ev(status="idle", speed_mps=2.0))


def test_position_jump_uses_physical_limit():
    prev = {"lat": 37.0, "lon": -122.0, "last_timestamp": T0, "battery_pct": 80, "status": "moving",
            "speed_mps": 1.0, "active_anomaly_types": []}
    e = ev(lat=38.0, lon=-122.0, ts=T0 + timedelta(seconds=1))
    assert "position_jump" in types(prev, e)


def test_battery_drain_rate():
    prev = {"lat": 37.0, "lon": -122.0, "last_timestamp": T0, "battery_pct": 80, "status": "moving",
            "speed_mps": 1.0, "active_anomaly_types": []}
    e = ev(battery_pct=70, ts=T0 + timedelta(seconds=1))  # 10%/s > 2%/s
    assert "battery_drain" in types(prev, e)


def test_normal_event_has_no_anomalies():
    assert types(None, ev()) == set()
