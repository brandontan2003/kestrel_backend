from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.config import get_db
from app.dto.theses import QuantConditionRequest, UpdateQuantConditionRequest
from app.models import QuantCondition
from app.models.theses import Theses


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

    async def get_quant_condition_by_id_and_user(self, quant_condition_id: str, theses_id: str,
                                                 user_id: str) -> QuantCondition | None:
        result = await self._db.execute(
            select(QuantCondition)
            .join(Theses, Theses.theses_id == QuantCondition.theses_id)
            .where(
                QuantCondition.quant_condition_id == quant_condition_id,
                QuantCondition.theses_id == theses_id,
                Theses.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_quant_condition(self, qc: QuantCondition, request: UpdateQuantConditionRequest) -> QuantCondition:
        metric = request.metric
        if metric is not None:
            qc.metric = metric

        operator = request.operator
        if operator is not None:
            qc.operator = operator

        value = request.value
        if value is not None:
            qc.value = value

        enabled = request.enabled
        if enabled is not None:
            qc.enabled = enabled
        await self._db.flush()
        return qc

    async def delete_quant_condition(self, quant_condition: QuantCondition) -> None:
        quant_condition.enabled = False
        await self._db.flush()


async def get_quant_condition_repository(db: AsyncSession = Depends(get_db)) -> QuantConditionRepository:
    return QuantConditionRepository(db)
