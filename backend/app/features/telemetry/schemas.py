from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.domain import VehicleStatus
from app.core.zones import ZONE_SET


class TelemetryEvent(BaseModel):
    vehicle_id: str
    ts: datetime
    lat: float
    lon: float
    battery_pct: int = Field(ge=0, le=100)
    speed_mps: float = Field(ge=0)
    status: VehicleStatus
    error_codes: list[str] = Field(default_factory=list)
    zone_entered: str | None = None

    @field_validator("zone_entered")
    @classmethod
    def zone_must_be_known(cls, v: str | None) -> str | None:
        if v is not None and v not in ZONE_SET:
            raise ValueError(f"unknown zone_entered: {v}")
        return v


class DetectedAnomaly(BaseModel):
    type: str
    severity: str


class IngestResult(BaseModel):
    detected_anomalies: list[DetectedAnomaly] = Field(default_factory=list)


class BatchItemResult(BaseModel):
    vehicle_id: str
    ts: datetime
    accepted: bool
    error: str | None = None
    detected_anomalies: list[DetectedAnomaly] = Field(default_factory=list)
