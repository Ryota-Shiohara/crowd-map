from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api.routes_health import router as health_router
from .api.routes_occupancy import router as occupancy_router
from .config import settings
from .domain.state_store import OccupancyStateStore
from .serial_worker import SerialWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    state_store = OccupancyStateStore(settings.initial_counts)
    state_store.bind_event_loop(asyncio.get_running_loop())
    worker = SerialWorker(state_store)

    app.state.occupancy_state_store = state_store
    app.state.serial_worker = worker

    worker.start()
    try:
        yield
    finally:
        worker.stop()


app = FastAPI(title="Crowd Map Occupancy API", lifespan=lifespan)
app.include_router(health_router)
app.include_router(occupancy_router)


@app.get("/")
async def root():
    return JSONResponse(
        {
            "service": "Crowd Map Occupancy API",
            "health": "/health",
            "occupancy": "/api/occupancy",
            "sse": "/api/occupancy/sse",
        }
    )
