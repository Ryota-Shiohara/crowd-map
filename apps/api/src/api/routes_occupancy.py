from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .sse_stream import occupancy_event_generator

router = APIRouter(prefix="/api")


@router.get("/occupancy")
async def get_occupancy(request: Request):
    store = request.app.state.occupancy_state_store
    if store is None:
        raise HTTPException(status_code=503, detail="State not initialized")
    return store.snapshot()


@router.get("/occupancy/sse")
async def get_occupancy_sse(request: Request):
    store = request.app.state.occupancy_state_store
    if store is None:
        raise HTTPException(status_code=503, detail="State not initialized")

    return StreamingResponse(
        occupancy_event_generator(store),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
