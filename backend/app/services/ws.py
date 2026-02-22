import asyncio
from collections import defaultdict

from fastapi import WebSocket


ALLOWED_CHANNELS = {"prices", "positions", "rfq_updates", "trade_updates"}


class ConnectionManager:
    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._channels[channel].add(websocket)

    async def disconnect(self, channel: str, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._channels[channel]:
                self._channels[channel].remove(websocket)

    async def broadcast(self, channel: str, payload: dict) -> None:
        async with self._lock:
            sockets = list(self._channels[channel])

        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except RuntimeError:
                stale.append(socket)
            except Exception:
                stale.append(socket)

        if stale:
            async with self._lock:
                for socket in stale:
                    self._channels[channel].discard(socket)


manager = ConnectionManager()
