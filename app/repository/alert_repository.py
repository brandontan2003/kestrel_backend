from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select, func

from app.config import get_db
from app.models import Alert


class AlertRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_all_alerts_by_user_id(self, user_id: str, page: int, page_size: int) -> tuple[list[Alert], int]:
        offset = (page - 1) * page_size
        count_result = await self._db.execute(
            select(func.count()).select_from(Alert).where(Alert.user_id == user_id))
        total = count_result.scalar_one()

        result = await self._db.execute(
            select(Alert)
            .where(Alert.user_id == user_id)
            .order_by(Alert.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total


async def get_alert_repository(db: AsyncSession = Depends(get_db)) -> AlertRepository:
    return AlertRepository(db)
