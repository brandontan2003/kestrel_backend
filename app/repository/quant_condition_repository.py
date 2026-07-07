from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_db
from app.dto.theses import QuantConditionRequest
from app.models import Catalyst, QuantCondition


class QuantConditionRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def bulk_create_quant_condition(self, theses_id: str, quant_conditions: list[QuantConditionRequest]) -> None:
        objects = [
            QuantCondition(
                theses_id=theses_id,
                metric=qc.metric,
                operator=qc.operator,
                value=qc.value,
            )
            for qc in quant_conditions
        ]
        self._db.add_all(objects)
        await self._db.flush()

    async def create_quant_condition(self, theses_id: str, metric: str, operator: str, value) -> QuantCondition:
        quant_condition = QuantCondition(
            theses_id=theses_id,
            metric=metric,
            operator=operator,
            value=value,
        )
        self._db.add(quant_condition)
        await self._db.flush()
        await self._db.refresh(quant_condition)
        return quant_condition


async def get_quant_condition_repository(db: AsyncSession = Depends(get_db)) -> QuantConditionRepository:
    return QuantConditionRepository(db)
