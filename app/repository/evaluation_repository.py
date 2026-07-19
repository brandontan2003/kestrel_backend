from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import func, select

from app.config import get_db
from app.models import Evaluation, Theses


class EvaluationRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_evaluation(self, theses_id: str, evaluation_status: str, prompt_version: str,
                                results: dict, signal: bool, reason: str | None = None) -> Evaluation:
        evaluation = Evaluation(
            theses_id=theses_id,
            evaluation_status=evaluation_status,
            prompt_version=prompt_version,
            results=results,
            signal=signal,
            reason=reason
        )
        self._db.add(evaluation)
        await self._db.flush()
        await self._db.refresh(evaluation)
        return evaluation

    async def get_latest_evaluation(self, theses_id) -> Evaluation | None:
        result = await self._db.execute(
            select(Evaluation).where(Evaluation.theses_id == theses_id).order_by(Evaluation.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def get_latest_evaluations_by_user_id(self, theses_ids: list[str]) -> dict[str, Evaluation]:
        if not theses_ids:
            return {}

        # Window function: rank evaluations per thesis by created_at desc
        row_number = (
            func.row_number()
            .over(
                partition_by=Evaluation.theses_id,
                order_by=Evaluation.created_at.desc()
            )
            .label("rn")
        )

        subquery = (
            select(Evaluation, row_number)
            .where(Evaluation.theses_id.in_(theses_ids))
            .subquery()
        )

        EvaluationAlias = aliased(Evaluation, subquery)

        result = await self._db.execute(
            select(EvaluationAlias).where(subquery.c.rn == 1)
        )

        evaluations = result.scalars().all()
        # Return as dict keyed by theses_id for O(1) lookup in the service
        return {e.theses_id: e for e in evaluations}

    async def get_evaluation_by_evaluation_id_and_user_id(self, evaluation_id: str, user_id: str) -> Evaluation | None:
        result = await self._db.execute(
            select(Evaluation)
            .join(Theses, Theses.theses_id == Evaluation.theses_id)
            .where(
                Evaluation.evaluation_id == evaluation_id,
                Theses.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_evaluation_by_theses_id(self, theses_id: str, page: int,
                                              page_size: int) -> tuple[list[Evaluation], int]:
        offset = (page - 1) * page_size
        count_result = await self._db.execute(
            select(func.count()).select_from(Evaluation).where(Evaluation.theses_id == theses_id))
        total = count_result.scalar_one()

        result = await self._db.execute(
            select(Evaluation)
            .where(Evaluation.theses_id == theses_id)
            .order_by(Evaluation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total


async def get_evaluation_repository(db: AsyncSession = Depends(get_db)) -> EvaluationRepository:
    return EvaluationRepository(db)
