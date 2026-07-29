from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.database_dependency import get_db
from app.dto.telegram import UpdateTelegramDetailRequest
from app.models.users import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_email(self, email_address: str) -> User:
        result = await self._db.execute(select(User).where(User.email == email_address))
        user = result.scalar_one_or_none()
        if user:
            await self._db.refresh(user)
        return user

    async def get_by_user_id(self, user_id: str) -> User:
        result = await self._db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            await self._db.refresh(user)
        return user

    async def create_user(self, email: str, username: str, password_hash: str) -> User:
        user = User(email=email, username=username, password_hash=password_hash)
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def update_user_telegram_details(self, user: User, request: UpdateTelegramDetailRequest) -> User:
        user.telegram_chat_id = request.chat_id
        user.telegram_handle = request.handle
        user.telegram_link_token = request.token
        user.telegram_token_expires_at = request.expires_at

        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def get_by_not_expired_telegram_token(self, token: str) -> User | None:
        result = await self._db.execute(
            select(User).where(
                User.telegram_link_token == token,
                User.telegram_token_expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)
