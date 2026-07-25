from typing import Optional

from fastapi import Depends, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.websockets import WebSocket

from app.core.authorization.auth_utility import ACCESS_COOKIE_KEY
from app.core.authorization.security import decode_token
from app.enums.AuthorizationEnum import AuthorizationTypeEnum
from app.enums.UserEnum import UserStatusEnum
from app.exception_handler import InvalidAuthTokenException, InvalidUserException
from app.models import User
from app.repository.user_repository import UserRepository, get_user_repository

# auto_error=False so we can fall back to cookie without FastAPI raising a 403 when the Authorization header is absent
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        access_token_cookie: Optional[str] = Cookie(default=None, alias=ACCESS_COOKIE_KEY),
        repo: UserRepository = Depends(get_user_repository)):
    token: Optional[str] = None

    if access_token_cookie:
        token = access_token_cookie
    elif credentials:
        token = credentials.credentials

    if token is None:
        raise InvalidAuthTokenException()

    payload = decode_token(token)
    if payload is None or payload.get("type") != AuthorizationTypeEnum.ACCESS.value:
        raise InvalidAuthTokenException()

    user = await repo.get_by_user_id(payload.get("sub"))
    if user is None or user.user_status != UserStatusEnum.ACTIVE.value:
        raise InvalidUserException()

    return user


async def get_current_user_ws(websocket: WebSocket, repo: UserRepository = Depends(get_user_repository)) -> User:
    # Try cookie first, fall back to query param
    token = websocket.cookies.get(ACCESS_COOKIE_KEY) or websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(code=1008)  # Policy violation
        raise InvalidAuthTokenException()

    payload = decode_token(token)
    if payload is None:
        await websocket.accept()
        await websocket.close(code=1008)
        raise InvalidAuthTokenException()

    user = await repo.get_by_user_id(payload["sub"])
    if user is None:
        await websocket.accept()
        await websocket.close(code=1008)
        raise InvalidAuthTokenException()
    return user
