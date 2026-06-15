"""Canonical domain vocabulary. StrEnum members compare and serialize as their string value, so
these are drop-in for the bare literals previously scattered across the slices — one source of truth."""
from enum import StrEnum


class VehicleStatus(StrEnum):
    IDLE = "idle"
    MOVING = "moving"
    CHARGING = "charging"
    FAULT = "fault"


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"


class AnomalyType(StrEnum):
    CRITICAL_BATTERY = "critical_battery"
    LOW_BATTERY = "low_battery"
    FAULT_STATUS = "fault_status"
    ERROR_CODE_PRESENT = "error_code_present"
    OVERSPEED = "overspeed"
    STATE_INCONSISTENT = "state_inconsistent"
    BATTERY_DRAIN = "battery_drain"
    CHARGING_NO_GAIN = "charging_no_gain"
    POSITION_JUMP = "position_jump"
    STALE_OFFLINE = "stale_offline"


class MissionStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    DONE = "done"


class MaintenanceStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
