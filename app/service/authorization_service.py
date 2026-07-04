from sqlite3 import IntegrityError

from fastapi import Depends

from app.core.authorization.security import hash_password, verify_password, create_access_token, create_refresh_token, \
    decode_token
from app.core.logger import logger
from app.dto.authorization import RegisterRequest, LoginRequest, TokenPair
from app.enums.AuthorizationEnum import AuthorizationTypeEnum
from app.enums.UserEnum import UserStatusEnum
from app.exception_handler import RegistrationErrorException, EmailAlreadyExistsException, InvalidCredentialsException, \
    InvalidAuthTokenException, InvalidUserException
from app.repository.user_repository import UserRepository, get_user_repository

# A real bcrypt hash of a throwaway value.
# Used so verify_password() is always called during login regardless of whether
# the email exists — bcrypt takes ~100ms and its absence would leak via response time.
_DUMMY_HASH = "$2a$12$mI064yKiULzmvf3ybZaW.OZjhqlHfoppy7R.ouDqnhyqMQryKHD8u"


class AuthorizationService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    async def register_user(self, request: RegisterRequest) -> TokenPair:
        user_existing = await self._repo.get_by_email(request.email)
        if user_existing:
            raise EmailAlreadyExistsException()
        try:
            user = await self._repo.create_user(
                email=request.email,
                username=request.username,
                password_hash=hash_password(request.password),
            )
        except EmailAlreadyExistsException:
            raise
        # Handle race condition: two requests passed the duplicate check simultaneously.
        except IntegrityError:
            raise EmailAlreadyExistsException()
        except Exception as ex:
            logger.error("Registration failed for %s: %s", request.email, ex, exc_info=True)
            raise RegistrationErrorException()

        return TokenPair(
            access_token=create_access_token(user.user_id),
            refresh_token=create_refresh_token(user.user_id),
        )

    async def login_user(self, request: LoginRequest) -> TokenPair:
        user = await self._repo.get_by_email(request.email)

        stored_hash = user.password_hash if user else _DUMMY_HASH
        password_ok = verify_password(request.password, stored_hash)

        if not user or not password_ok or user.user_status != UserStatusEnum.ACTIVE.value:
            raise InvalidCredentialsException()

        return TokenPair(
            access_token=create_access_token(user.user_id),
            refresh_token=create_refresh_token(user.user_id),
        )

    async def refresh(self, refresh_token: str | None) -> TokenPair:
        if refresh_token is None:
            raise InvalidAuthTokenException()

        payload = decode_token(refresh_token)
        if payload is None or payload.get("type") != AuthorizationTypeEnum.REFRESH.value:
            raise InvalidAuthTokenException()

        user = await self._repo.get_by_user_id(payload.get("sub"))
        if user is None or user.user_status != UserStatusEnum.ACTIVE.value:
            raise InvalidUserException()

        return TokenPair(
            access_token=create_access_token(user.user_id),
            refresh_token=create_refresh_token(user.user_id),
        )


async def get_authorization_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthorizationService:
    return AuthorizationService(user_repo)
