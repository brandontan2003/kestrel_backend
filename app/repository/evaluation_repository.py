from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.config import get_db
from app.models import Evaluation


class EvaluationRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_latest_evaluation(self, theses_id) -> Evaluation | None:
        result = await self._db.execute(select(Evaluation).where(Evaluation.theses_id == theses_id).order_by(Evaluation.created_at.desc()).limit(1))
        return result.scalar_one_or_none()


async def get_evaluation_repository(db: AsyncSession = Depends(get_db)) -> EvaluationRepository:
    return EvaluationRepository(db)
