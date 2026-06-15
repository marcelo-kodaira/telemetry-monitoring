import logging

from fastapi import APIRouter, status

from app.core.db import transaction
from app.features.telemetry.ingest import ingest_event
from app.features.telemetry.schemas import BatchItemResult, IngestResult, TelemetryEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, summary="Ingest a telemetry event")
async def post_telemetry(event: TelemetryEvent) -> IngestResult:
    async with transaction() as conn:
        return await ingest_event(conn, event)


@router.post("/batch", summary="Ingest a batch of telemetry events (per-event transactions)")
async def post_batch(events: list[TelemetryEvent]) -> list[BatchItemResult]:
    results: list[BatchItemResult] = []
    for e in events:
        try:
            async with transaction() as conn:
                res = await ingest_event(conn, e)
            results.append(
                BatchItemResult(
                    vehicle_id=e.vehicle_id, ts=e.ts, accepted=True,
                    detected_anomalies=res.detected_anomalies,
                )
            )
        except Exception as exc:  # best-effort: one bad event must not abort the batch
            logger.warning("batch ingest failed for %s @ %s: %s", e.vehicle_id, e.ts, exc)
            results.append(
                BatchItemResult(vehicle_id=e.vehicle_id, ts=e.ts, accepted=False, error=str(exc))
            )
    return results
