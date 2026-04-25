import asyncio
import json


async def occupancy_event_generator(state_store):
    queue = state_store.subscribe()
    try:
        yield f"data: {json.dumps(state_store.snapshot())}\n\n"

        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15)
                yield f"data: {json.dumps(message)}\n\n"
            except asyncio.TimeoutError:
                # Keep-alive ping
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        state_store.unsubscribe(queue)
        raise
