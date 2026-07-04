from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings
from app.enums.AuthorizationEnum import AuthorizationTypeEnum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


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
