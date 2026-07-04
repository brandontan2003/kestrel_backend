from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.config import get_db
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


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)
