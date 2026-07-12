from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.authorization.auth_dependency import get_current_user_ws
from app.models.users import User
from app.websocket.connection_manager import manager
from app.websocket.handler import handle_message

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, current_user: User = Depends(get_current_user_ws)) -> None:
    user_id = current_user.user_id
    await manager.connect(user_id, websocket)
    try:
        while True:
            await handle_message(user_id, websocket)
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
