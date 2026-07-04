from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.authorization.security import decode_token
from app.enums.AuthorizationEnum import AuthorizationTypeEnum
from app.enums.UserEnum import UserStatusEnum
from app.exception_handler import InvalidAuthTokenException, InvalidUserException
from app.models.users import User
from app.repository.user_repository import UserRepository, get_user_repository

bearer_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                           repo: UserRepository = Depends(get_user_repository)) -> User:
    payload = decode_token(credentials.credentials)

    if payload is None or payload.get("type") != AuthorizationTypeEnum.ACCESS.value:
        raise InvalidAuthTokenException()

    user = await repo.get_by_user_id(payload.get("sub"))

    if user is None or user.user_status != UserStatusEnum.ACTIVE.value:
        raise InvalidUserException()

    return user
