from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.core.db import apply_schema, close_pool, init_pool
from app.features.anomalies.router import router as anomalies_router
from app.features.anomalies.staleness import start_staleness_sweep, stop_staleness_sweep
from app.features.fleet.router import router as fleet_router
from app.features.telemetry.router import router as telemetry_router
from app.features.vehicles.router import router as vehicles_router
from app.features.zones.router import router as zones_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    await apply_schema()
    task = start_staleness_sweep()
    yield
    await stop_staleness_sweep(task)
    await close_pool()


app = FastAPI(title="Fleet Telemetry Monitoring", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dashboard is read-only on a trusted network; tighten per-origin in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (telemetry_router, vehicles_router, zones_router, anomalies_router, fleet_router):
    app.include_router(r)


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title="Fleet Telemetry API")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
