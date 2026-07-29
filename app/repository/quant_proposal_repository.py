from datetime import timezone, datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select, func

from app.database_dependency import get_db
from app.models import QuantProposal, Theses
from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum


class QuantProposalRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_quant_proposal_id_and_user_id(self, proposal_id: str, user_id: str) -> QuantProposal | None:
        result = await self._db.execute(
            select(QuantProposal)
            .join(Theses, Theses.theses_id == QuantProposal.theses_id)
            .where(QuantProposal.quant_proposal_id == proposal_id, Theses.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all_quant_proposal_by_user(self, user_id: str, page: int, page_size: int,
                                             status: str | None = None) -> tuple[list[QuantProposal], int]:
        base = (
            select(QuantProposal)
            .join(Theses, Theses.theses_id == QuantProposal.theses_id)
            .where(Theses.user_id == user_id)
        )
        if status:
            base = base.where(QuantProposal.quant_proposal_status == status)

        count_result = await self._db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        rows = await self._db.execute(base.offset(offset).limit(page_size))
        return list(rows.scalars().all()), total

    async def create_quant_proposal(self, theses_id: str, quant_condition_id: str | None, proposal_type: str,
                                    proposed_change: dict, llm_rationale: str | None,
                                    llm_confidence: float | None, source_article_url: str | None,
                                    source_evaluation_id: str) -> QuantProposal:
        proposal = QuantProposal(
            theses_id=theses_id,
            quant_condition_id=quant_condition_id,
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

    async def get_pending_by_theses_id(self, theses_id: str) -> list[QuantProposal]:
        """Every still-pending proposal on a thesis — the generator's dedup set,
        so a repeat sweep doesn't queue the same suggestion twice."""
        result = await self._db.execute(
            select(QuantProposal).where(
                QuantProposal.theses_id == theses_id,
                QuantProposal.quant_proposal_status == ProposalStatusEnum.PENDING,
            )
        )
        return list(result.scalars().all())

    async def get_pending_updates_for_condition(self, quant_condition_id: str,
                                                exclude_proposal_id: str) -> list[QuantProposal]:
        """Return all other pending UPDATE proposals for the same quant condition."""
        result = await self._db.execute(
            select(QuantProposal).where(
                QuantProposal.quant_condition_id == quant_condition_id,
                QuantProposal.proposal_type == ProposalTypeEnum.UPDATE,
                QuantProposal.quant_proposal_status == ProposalStatusEnum.PENDING,
                QuantProposal.quant_proposal_id != exclude_proposal_id,
            )
        )
        return list(result.scalars().all())

    async def supersede_pending_updates(self, quant_condition_id: str, approved_proposal_id: str) -> None:
        """Auto-reject all other pending UPDATE proposals for the same condition_id."""
        superseded = await self.get_pending_updates_for_condition(quant_condition_id=quant_condition_id,
                                                                  exclude_proposal_id=approved_proposal_id)
        reason = f"Superseded by approval of {approved_proposal_id}"
        for proposal in superseded:
            await self.reject_quant_proposal(proposal, rejection_reason=reason)

    async def approve_quant_proposal(self, proposal: QuantProposal) -> QuantProposal:
        proposal.quant_proposal_status = ProposalStatusEnum.APPROVED
        proposal.resolved_at = datetime.now(timezone.utc)
        await self._db.flush()
        return proposal

    async def reject_quant_proposal(self, proposal: QuantProposal, rejection_reason: str) -> QuantProposal:
        proposal.quant_proposal_status = ProposalStatusEnum.REJECTED
        proposal.rejection_reason = rejection_reason
        proposal.resolved_at = datetime.now(timezone.utc)
        await self._db.flush()
        return proposal


async def get_quant_proposal_repository(db: AsyncSession = Depends(get_db)) -> QuantProposalRepository:
    return QuantProposalRepository(db)
