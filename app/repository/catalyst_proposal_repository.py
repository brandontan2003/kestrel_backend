from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select, func

from app.config import get_db
from app.models import CatalystProposal, Theses


class CatalystProposalRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_catalyst_proposal_id(self, proposal_id: str) -> CatalystProposal | None:
        result = await self._db.execute(
            select(CatalystProposal).where(
                CatalystProposal.catalyst_proposal_id == proposal_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_catalyst_proposal_by_user(self, user_id: str, page: int, page_size: int,
                                                status: str | None = None) -> tuple[list[CatalystProposal], int]:
        base = (
            select(CatalystProposal)
            .join(Theses, Theses.theses_id == CatalystProposal.theses_id)
            .where(Theses.user_id == user_id)
        )
        if status:
            base = base.where(CatalystProposal.catalyst_proposal_status == status)

        count_result = await self._db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        rows = await self._db.execute(base.offset(offset).limit(page_size))
        return list(rows.scalars().all()), total


async def get_catalyst_proposal_repository(db: AsyncSession = Depends(get_db)) -> CatalystProposalRepository:
    return CatalystProposalRepository(db)
