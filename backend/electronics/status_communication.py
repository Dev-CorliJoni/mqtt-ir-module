import asyncio
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket


class StatusCommunication:
    def __init__(self) -> None:
        # Track active WebSocket connections for status updates.
        self._connections: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock: Optional[asyncio.Lock] = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        # Store the running event loop so sync code can schedule async broadcasts.
        self._loop = loop
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._get_lock():
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._get_lock():
            self._connections.discard(websocket)

    async def send(self, websocket: WebSocket, payload: Dict[str, Any]) -> None:
        # Keep single-client sends separate from broadcast for clarity.
        await websocket.send_json(payload)

    def broadcast(self, payload: Dict[str, Any]) -> None:
        # Do not block sync callers; schedule the async send on the event loop.
        if not self._loop:
            return

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop and running_loop is self._loop:
            self._loop.create_task(self._broadcast_async(payload))
        else:
            asyncio.run_coroutine_threadsafe(self._broadcast_async(payload), self._loop)

    async def _broadcast_async(self, payload: Dict[str, Any]) -> None:
        async with self._get_lock():
            connections = list(self._connections)
        if not connections:
            return

        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)

        if stale:
            async with self._get_lock():
                for websocket in stale:
                    self._connections.discard(websocket)

    def _get_lock(self) -> asyncio.Lock:
        # Lazily create the lock in the active event loop.
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
