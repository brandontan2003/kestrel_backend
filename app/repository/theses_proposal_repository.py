from datetime import timezone, datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select, func

from app.config import get_db
from app.models import ThesesProposal
from common.enums.ProposalEnum import ProposalStatusEnum


class ThesesProposalRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_theses_proposal_id_and_user_id(self, proposal_id: str, user_id: str) -> ThesesProposal | None:
        result = await self._db.execute(
            select(ThesesProposal).where(
                ThesesProposal.theses_proposal_id == proposal_id, ThesesProposal.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_theses_proposal_by_user(self, user_id: str, page: int, page_size: int,
                                              status: str | None = None) -> tuple[list[ThesesProposal], int]:
        base = select(ThesesProposal).where(ThesesProposal.user_id == user_id)
        if status:
            base = base.where(ThesesProposal.theses_proposal_status == status)

        count_result = await self._db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        rows = await self._db.execute(base.offset(offset).limit(page_size))
        return list(rows.scalars().all()), total

    async def approve_theses_proposal(self, proposal: ThesesProposal) -> ThesesProposal:
        proposal.theses_proposal_status = ProposalStatusEnum.APPROVED
        proposal.resolved_at = datetime.now(timezone.utc)
        await self._db.flush()
        return proposal

    async def reject_theses_proposal(self, proposal: ThesesProposal, rejection_reason: str) -> ThesesProposal:
        proposal.theses_proposal_status = ProposalStatusEnum.REJECTED
        proposal.rejection_reason = rejection_reason
        proposal.resolved_at = datetime.now(timezone.utc)
        await self._db.flush()
        return proposal


async def get_theses_proposal_repository(db: AsyncSession = Depends(get_db)) -> ThesesProposalRepository:
    return ThesesProposalRepository(db)
