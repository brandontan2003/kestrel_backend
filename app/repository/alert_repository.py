from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select, func

from app.database_dependency import get_db
from app.dto.alert import CreateAlertRequest
from app.models import Alert
from common.enums.AlertsEnum import AlertStatusEnum


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

    async def get_alert_by_alert_id_and_user_id(self, alert_id: str, user_id: str) -> Alert | None:
        result = await self._db.execute(select(Alert).where(Alert.alert_id == alert_id, Alert.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_alert(self, request: CreateAlertRequest) -> Alert:
        alert = Alert(evaluation_id=request.evaluation_id, user_id=request.user_id, channels_sent=request.channels_sent)
        self._db.add(alert)
        await self._db.flush()
        await self._db.refresh(alert)
        return alert

    async def update_alert_status(self, alert: Alert, status: AlertStatusEnum) -> None:
        alert.alert_status = status
        await self._db.flush()


async def get_alert_repository(db: AsyncSession = Depends(get_db)) -> AlertRepository:
    return AlertRepository(db)
