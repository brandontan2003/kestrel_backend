from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from app.config import settings
from app.enums.AuthorizationEnum import AuthorizationTypeEnum


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_jwt_payload(expire: datetime, user_id: str, auth_type: AuthorizationTypeEnum):
    return {"sub": user_id, "exp": expire, "type": auth_type.value}


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(create_jwt_payload(expire, user_id, AuthorizationTypeEnum.ACCESS), settings.JWT_SECRET_KEY,
                      algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(create_jwt_payload(expire, user_id, AuthorizationTypeEnum.REFRESH), settings.JWT_SECRET_KEY,
                      algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
