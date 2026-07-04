from typing import Optional

from fastapi import APIRouter, Depends, Response, Cookie

from app.core.authorization.auth_dependency import get_current_user
from app.core.authorization.auth_utility import set_refresh_cookie, REFRESH_COOKIE_KEY, clear_refresh_cookie
from app.dto.authorization import RegisterRequest, AccessTokenResponse, LoginRequest
from app.dto.base import SuccessResponse, DataResponse
from app.models.users import User
from app.service.authorization_service import AuthorizationService, get_authorization_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=DataResponse[AccessTokenResponse], status_code=201)
async def register(payload: RegisterRequest, response: Response,
                   service: AuthorizationService = Depends(get_authorization_service)):
    """
    Create a new account.
    Returns an access token in the body and sets a refresh token HttpOnly cookie.
    """
    token_pair = await service.register_user(payload)
    set_refresh_cookie(response, token_pair.refresh_token)
    return DataResponse(result=AccessTokenResponse(access_token=token_pair.access_token))


@router.post("/login", response_model=DataResponse[AccessTokenResponse])
async def login(payload: LoginRequest, response: Response,
                service: AuthorizationService = Depends(get_authorization_service)):
    """
    Authenticate with email + password.
    Returns an access token in the body and sets a refresh token HttpOnly cookie.

    Intentionally uses a single generic error for wrong email OR wrong password.
    """
    token_pair = await service.login_user(payload)
    set_refresh_cookie(response, token_pair.refresh_token)
    return DataResponse(result=AccessTokenResponse(access_token=token_pair.access_token))


@router.post("/refresh", response_model=DataResponse[AccessTokenResponse])
async def refresh(response: Response, service: AuthorizationService = Depends(get_authorization_service),
                  refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_KEY)):
    """
    Issue a new access token using the refresh token from the HttpOnly cookie.
    Also rotates the refresh token (new cookie issued, old one logically invalidated).
    """
    token_pair = await service.refresh(refresh_token)
    set_refresh_cookie(response, token_pair.refresh_token)
    return DataResponse(result=AccessTokenResponse(access_token=token_pair.access_token))


@router.post("/logout", response_model=SuccessResponse)
async def logout(response: Response, _: User = Depends(get_current_user)):
    """
    Clear the refresh token cookie. Access token expiry is handled client-side
    (drop it from memory; it expires in 15 min regardless).
    Requires a valid access token so random callers can't spam this endpoint.
    """
    clear_refresh_cookie(response)
    return SuccessResponse()
