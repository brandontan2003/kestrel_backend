import json

from fastapi import WebSocket
from pydantic import ValidationError


async def handle_message(user_id: str, websocket: WebSocket) -> None:
    try:
        await websocket.receive_json()
    except json.JSONDecodeError:
        await websocket.send_text(json.dumps({"error": "invalid JSON"}))
        return
    except ValidationError as e:
        await websocket.send_text(json.dumps({"error": e.errors()}))
        return
