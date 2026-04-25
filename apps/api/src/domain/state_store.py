import asyncio
from datetime import datetime
from typing import Dict, List


class OccupancyStateStore:
    def __init__(self, initial_counts: Dict[str, int]):
        self.room_counts = dict(initial_counts)
        self.last_event = None
        self.updated_at = datetime.now().isoformat()
        self.sequence = 0
        self.subscribers: List[asyncio.Queue] = []
        self._event_loop = None

    def bind_event_loop(self, event_loop: asyncio.AbstractEventLoop):
        self._event_loop = event_loop

    def snapshot(self) -> dict:
        return {
            "room_counts": dict(self.room_counts),
            "last_event": self.last_event,
            "updated_at": self.updated_at,
            "sequence": self.sequence,
        }

    def update(self, room_counts: Dict[str, int], event_label: str, from_room: str, to_room: str):
        self.room_counts = dict(room_counts)
        self.sequence += 1
        now = datetime.now().isoformat()
        self.last_event = {
            "event_label": event_label,
            "from_room": from_room,
            "to_room": to_room,
            "timestamp": now,
        }
        self.updated_at = now
        if self._event_loop is not None:
            asyncio.run_coroutine_threadsafe(self._notify_all(), self._event_loop)

    async def _notify_all(self):
        message = self.snapshot()
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)
