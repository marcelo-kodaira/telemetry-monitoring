from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Status = Literal["idle", "moving", "charging", "fault"]


class StatusUpdate(BaseModel):
    status: Status
    reason: str | None = None


class StatusResult(BaseModel):
    vehicle_id: str
    status: str
    fault_handled: bool = False
    maintenance_id: int | None = None
    mission_cancelled: bool = False


class LatestAnomaly(BaseModel):
    type: str
    severity: str
    detected_at: datetime


class VehicleView(BaseModel):
    vehicle_id: str
    status: str
    battery_pct: int
    lat: float | None = None
    lon: float | None = None
    is_offline: bool
    last_seen_at: datetime | None = None
    latest_anomaly: LatestAnomaly | None = None
