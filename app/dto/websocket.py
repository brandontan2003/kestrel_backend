from pydantic import BaseModel

from app.enums.WebSocketEnum import WebSocketEventTypeEnum


class AlertPayload(BaseModel):
    alert_id: str
    theses_id: str
    alert_type: str


class WebSocketInboundEvent(BaseModel):
    event_type: WebSocketEventTypeEnum
    payload: AlertPayload
