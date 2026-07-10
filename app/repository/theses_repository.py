from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import func, select

from app.config import get_db
from app.dto.theses import UpdateThesesRequest
from app.enums.ThesesEnum import ThesesStatusEnum
from app.models import Theses


class ThesesRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_theses(self, user_id: str, stock_id: str, quant_mode: str, catalyst_mode: str,
                            notes: str | None) -> Theses:
        theses = Theses(
            user_id=user_id,
            stock_id=stock_id,
            quant_mode=quant_mode,
            catalyst_mode=catalyst_mode,
            notes=notes,
        )
        self._db.add(theses)
        await self._db.flush()
        await self._db.refresh(theses)
        return theses

    async def delete_theses(self, theses: Theses) -> None:
        theses.theses_status = ThesesStatusEnum.DELETED

        for condition in theses.quant_conditions_mapping:
            condition.enabled = False

        for catalyst in theses.catalyst_mapping:
            catalyst.enabled = False

        await self._db.flush()

    async def update_theses(self, theses: Theses, request: UpdateThesesRequest) -> Theses:
        theses_status = request.theses_status
        if theses_status is not None:
            theses.theses_status = theses_status

        quant_mode = request.quant_mode
        if quant_mode is not None:
            theses.quant_mode = quant_mode

        catalyst_mode = request.catalyst_mode
        if catalyst_mode is not None:
            theses.catalyst_mode = catalyst_mode

        notes = request.notes
        if notes is not None:
            if notes == "<None>":
                theses.notes = None
            else:
                theses.notes = notes
        await self._db.flush()
        return theses

    async def expire_theses(self, theses: Theses) -> None:
        self._db.expire(theses)

    async def get_theses_by_theses_id(self, theses_id) -> Theses | None:
        result = await self._db.execute(select(Theses).where(Theses.theses_id == theses_id))
        return result.scalar_one_or_none()

    async def get_all_theses_by_user_id(self, user_id: str, page: int, page_size: int) -> tuple[list[Theses], int]:
        offset = (page - 1) * page_size
        count_result = await self._db.execute(select(func.count()).select_from(Theses).where(Theses.user_id == user_id))
        total = count_result.scalar_one()

        # Paginated fetch
        result = await self._db.execute(
            select(Theses)
            .where(Theses.user_id == user_id)
            .order_by(Theses.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total


async def get_theses_repository(db: AsyncSession = Depends(get_db)) -> ThesesRepository:
    return ThesesRepository(db)
