import json
from typing import Any

from fastapi import WebSocket

from app.core.logger import logger


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        logger.info("WebSocket connected: user_id=%s, active_connections=%d", user_id, self._total_connections())

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("WebSocket disconnected: user_id=%s, active_connections=%d", user_id, self._total_connections())

    async def push_to_user(self, user_id: str, event_type: str, payload: dict[str, Any]) -> None:
        connections = self._connections.get(user_id)
        if not connections:
            return

        message = json.dumps({"type": event_type, "payload": payload})
        stale: set[WebSocket] = set()

        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:
                logger.warning("Failed to send to WebSocket for user_id=%s, marking stale", user_id)
                stale.add(websocket)

        for websocket in stale:
            self.disconnect(user_id, websocket)

    def _total_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


manager = ConnectionManager()
