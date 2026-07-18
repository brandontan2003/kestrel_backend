from datetime import timezone, datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select, func

from app.config import get_db
from app.models import CatalystProposal, Theses
from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum


class CatalystProposalRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_catalyst_proposal_id_and_user_id(self, proposal_id: str, user_id: str) -> CatalystProposal | None:
        result = await self._db.execute(
            select(CatalystProposal)
            .join(Theses, Theses.theses_id == CatalystProposal.theses_id)
            .where(
                CatalystProposal.catalyst_proposal_id == proposal_id,
                Theses.user_id == user_id
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

    async def create_catalyst_proposal(self, theses_id: str, catalyst_id: str | None, proposal_type: str,
                                       proposed_change: dict, llm_rationale: str | None,
                                       llm_confidence: float | None, source_article_url: str | None,
                                       source_evaluation_id: str) -> CatalystProposal:
        proposal = CatalystProposal(
            theses_id=theses_id,
            catalyst_id=catalyst_id,
            proposal_type=proposal_type,
            proposed_change=proposed_change,
            llm_rationale=llm_rationale,
            llm_confidence=llm_confidence,
            source_article_url=source_article_url,
            source_evaluation_id=source_evaluation_id,
        )
        self._db.add(proposal)
        await self._db.flush()
        await self._db.refresh(proposal)
        return proposal

    async def get_pending_by_theses_id(self, theses_id: str) -> list[CatalystProposal]:
        """Every still-pending proposal on a thesis — the generator's dedup set,
        so a repeat sweep doesn't queue the same suggestion twice."""
        result = await self._db.execute(
            select(CatalystProposal).where(
                CatalystProposal.theses_id == theses_id,
                CatalystProposal.catalyst_proposal_status == ProposalStatusEnum.PENDING,
            )
        )
        return list(result.scalars().all())

    async def get_pending_updates_for_catalyst(self, catalyst_id: str,
                                               exclude_proposal_id: str) -> list[CatalystProposal]:
        """Return all other pending UPDATE proposals for the same catalyst."""
        result = await self._db.execute(
            select(CatalystProposal).where(
                CatalystProposal.catalyst_id == catalyst_id,
                CatalystProposal.proposal_type == ProposalTypeEnum.UPDATE,
                CatalystProposal.catalyst_proposal_status == ProposalStatusEnum.PENDING,
                # Exclude the proposal being approved — it's still PENDING here, so
                # matching on catalyst_id alone would sweep it into its own supersede
                # set and stamp a rejection reason onto an already-approved row.
                CatalystProposal.catalyst_proposal_id != exclude_proposal_id,
            )
        )
        return list(result.scalars().all())

    async def supersede_pending_updates(self, catalyst_id: str, approved_proposal_id: str) -> None:
        """Auto-reject all other pending UPDATE proposals for the same catalyst_id."""
        superseded = await self.get_pending_updates_for_catalyst(catalyst_id=catalyst_id,
                                                                 exclude_proposal_id=approved_proposal_id)
        reason = f"Superseded by approval of {approved_proposal_id}"
        for proposal in superseded:
            await self.reject_catalyst_proposal(proposal, rejection_reason=reason)

    async def approve_catalyst_proposal(self, proposal: CatalystProposal) -> CatalystProposal:
        proposal.catalyst_proposal_status = ProposalStatusEnum.APPROVED
        proposal.resolved_at = datetime.now(timezone.utc)
        await self._db.flush()
        return proposal

    async def reject_catalyst_proposal(self, proposal: CatalystProposal, rejection_reason: str) -> CatalystProposal:
        proposal.catalyst_proposal_status = ProposalStatusEnum.REJECTED
        proposal.rejection_reason = rejection_reason
        proposal.resolved_at = datetime.now(timezone.utc)
        await self._db.flush()
        return proposal


async def get_catalyst_proposal_repository(db: AsyncSession = Depends(get_db)) -> CatalystProposalRepository:
    return CatalystProposalRepository(db)
