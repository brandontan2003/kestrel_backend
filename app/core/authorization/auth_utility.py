from fastapi import Response

from app.config import settings

REFRESH_COOKIE_KEY = "refresh_token"


def set_refresh_cookie(response: Response, token: str) -> None:
    """Write the refresh token into an HttpOnly cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=settings.ENV != "dev",  # Secure flag off only in local dev (HTTP)
        samesite="strict",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/auth",  # Scoped: browser only sends it to auth endpoints
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_KEY, path="/api/v1/auth")
