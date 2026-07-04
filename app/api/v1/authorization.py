from typing import Optional

from fastapi import APIRouter, Depends, Response, Cookie

from app.config import settings
from app.core.authorization.auth_dependency import get_current_user
from app.core.authorization.auth_utility import set_auth_cookies, REFRESH_COOKIE_KEY, clear_auth_cookies
from app.dto.authorization import RegisterRequest, LoginRequest, AuthResponse
from app.dto.base import SuccessResponse, DataResponse
from app.dto.error import ErrorResponse
from app.enums.ErrorEnum import ErrorEnum
from app.models.users import User
from app.service.authorization_service import AuthorizationService, get_authorization_service

router = APIRouter(prefix="/auth", tags=["auth"])
_EXPIRES_IN = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post("/register", response_model=DataResponse[AuthResponse], status_code=201,
             responses={400: {"model": ErrorResponse, "description": ErrorEnum.EMAIL_ALREADY_EXISTS.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code},
                        500: {"model": ErrorResponse, "description": ErrorEnum.USER_REGISTRATION_FAILED.error_code},
                        })
async def register(payload: RegisterRequest, response: Response,
                   service: AuthorizationService = Depends(get_authorization_service)):
    """
    Create a new account.
    Returns an access token in the body and sets a refresh token HttpOnly cookie.
    """
    token_pair = await service.register_user(payload)
    set_auth_cookies(response, token_pair.access_token, token_pair.refresh_token)
    return DataResponse(result=AuthResponse(access_token=token_pair.access_token, expires_in=_EXPIRES_IN))


@router.post("/login", response_model=DataResponse[AuthResponse],
             responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_CREDENTIALS_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code},
                        })
async def login(payload: LoginRequest, response: Response,
                service: AuthorizationService = Depends(get_authorization_service)):
    """
    Authenticate with email + password.
    Returns an access token in the body and sets a refresh token HttpOnly cookie.

    Intentionally uses a single generic error for wrong email OR wrong password.
    """
    token_pair = await service.login_user(payload)
    set_auth_cookies(response, token_pair.access_token, token_pair.refresh_token)
    return DataResponse(result=AuthResponse(access_token=token_pair.access_token, expires_in=_EXPIRES_IN))


@router.post("/refresh", response_model=DataResponse[AuthResponse],
             responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code},
                        })
async def refresh(response: Response, service: AuthorizationService = Depends(get_authorization_service),
                  refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_KEY)):
    """
    Issue a new access token using the refresh token from the HttpOnly cookie.
    Also rotates the refresh token (new cookie issued, old one logically invalidated).
    """
    token_pair = await service.refresh(refresh_token)
    set_auth_cookies(response, token_pair.access_token, token_pair.refresh_token)
    return DataResponse(result=AuthResponse(access_token=token_pair.access_token, expires_in=_EXPIRES_IN))


@router.post("/logout", response_model=SuccessResponse,
             responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code}})
async def logout(response: Response, _: User = Depends(get_current_user)):
    """
        Clears BOTH cookies — access token and refresh token.
        Frontend MUST also drop the access token from memory/state on receipt of this 200.
        Access token remains cryptographically valid until expiry (max 15 min) —
        true revocation requires a blocklist table (v2).
    """
    clear_auth_cookies(response)
    return SuccessResponse()
