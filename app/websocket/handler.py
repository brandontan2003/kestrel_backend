import json

from fastapi import WebSocket
from pydantic import ValidationError

from app.dto.websocket import WebSocketInboundEvent, AlertPayload
from app.enums.WebSocketEnum import WebSocketEventTypeEnum


async def handle_message(user_id: str, websocket: WebSocket) -> None:
    try:
        data = await websocket.receive_json()
        event = WebSocketInboundEvent(**data)
    except json.JSONDecodeError:
        await websocket.send_text(json.dumps({"error": "invalid JSON"}))
        return
    except ValidationError as e:
        await websocket.send_text(json.dumps({"error": e.errors()}))
        return

    if event.event_type == WebSocketEventTypeEnum.ALERT:
        await handle_alert(user_id, event.payload, websocket)


async def handle_alert(user_id: str, payload: AlertPayload, websocket: WebSocket) -> None:
    # TODO: Processing logic here
    await websocket.send_text(json.dumps({
        "event_type": WebSocketEventTypeEnum.ALERT,
        "payload": {
            "alert_id": payload.alert_id,
            "theses_id": payload.theses_id,
            "alert_type": payload.alert_type
        }
    }))
