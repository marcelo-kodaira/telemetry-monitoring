from datetime import datetime

from pydantic import BaseModel


class AnomalyView(BaseModel):
    id: int
    vehicle_id: str
    type: str
    severity: str
    detected_at: datetime
    details: dict


class AnomalyListView(BaseModel):
    count: int
    anomalies: list[AnomalyView]
