
from fastapi import Response
from app.config import settings

REFRESH_COOKIE_KEY = "refresh_token"
ACCESS_COOKIE_KEY = "access_token"
_COOKIE_PATH = "/api/v1"        # widened from /api/v1/auth so access cookie is
                                 # sent to ALL protected endpoints, not just auth routes


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Sets both tokens as HttpOnly cookies.

    Access token:
    - Short max_age (matches JWT expiry) so the browser auto-expires it.
    - Sent to all /api/v1/* routes so protected endpoints receive it automatically.

    Refresh token:
    - Long max_age (7 days).
    - Scoped to /api/v1/auth only — browser will NOT send it to /api/v1/theses etc.
      Minimises the window in which the refresh token is transmitted.
    """
    response.set_cookie(
        key=ACCESS_COOKIE_KEY,
        value=access_token,
        httponly=True,
        secure=settings.ENV != "dev",
        samesite="strict",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=_COOKIE_PATH,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=refresh_token,
        httponly=True,
        secure=settings.ENV != "dev",
        samesite="strict",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=f"{_COOKIE_PATH}/auth",   # /api/v1/auth only
    )


def clear_auth_cookies(response: Response) -> None:
    """
    Deletes both cookies on logout.
    Must use the exact same path that was used to set each cookie,
    otherwise the browser ignores the delete instruction.
    """
    response.delete_cookie(key=ACCESS_COOKIE_KEY, path=_COOKIE_PATH)
    response.delete_cookie(key=REFRESH_COOKIE_KEY, path=f"{_COOKIE_PATH}/auth")
