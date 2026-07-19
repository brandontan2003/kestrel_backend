import uuid

from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, DECIMAL, Text
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import LAZY_SELECTIN, ModelName
from app.models.base import Base
from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum


class QuantProposalHistory(Base, Auditable):
    __tablename__ = "tbl_quant_proposals_history"

    quant_proposal_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quant_proposal_id = Column(String(36), ForeignKey("tbl_quant_proposals.quant_proposal_id"), nullable=False)

    theses_id = Column(String(36), nullable=False)
    quant_condition_id = Column(String(36))
    proposal_type = Column(String(36), nullable=False)

    proposed_change = Column(JSON, nullable=False)
    llm_rationale = Column(Text)
    llm_confidence = Column(DECIMAL(4, 3))

    source_article_url = Column(Text)
    source_evaluation_id = Column(String(36), nullable=False)
    quant_proposal_status = Column(String(15), nullable=False)
    rejection_reason = Column(Text)
    resolved_at = Column(DateTime(timezone=True))


@register_history(QuantProposalHistory)
class QuantProposal(Base, Auditable):
    __tablename__ = "tbl_quant_proposals"

    quant_proposal_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    theses_id = Column(String(36), ForeignKey("tbl_theses.theses_id"), nullable=False)
    # NULL for an ADD proposal — there's no condition row to point at until it's
    # approved. Matches V1.10's nullable column (and the history model above).
    quant_condition_id = Column(String(36), ForeignKey("tbl_quant_conditions.quant_condition_id"))
    proposal_type = Column(String(36), default=ProposalTypeEnum.UPDATE, nullable=False)

    proposed_change = Column(JSON, nullable=False)
    llm_rationale = Column(Text)
    llm_confidence = Column(DECIMAL(4, 3))

    source_article_url = Column(Text)
    source_evaluation_id = Column(String(36), ForeignKey("tbl_evaluations.evaluation_id"), nullable=False)
    quant_proposal_status = Column(String(15), default=ProposalStatusEnum.PENDING, nullable=False)
    rejection_reason = Column(Text)
    resolved_at = Column(DateTime(timezone=True))

    evaluations_mapping = relationship(
        ModelName.EVALUATION,
        back_populates="quant_proposals_mapping",
        lazy=LAZY_SELECTIN
    )

    theses_mapping = relationship(
        ModelName.THESES,
        back_populates="quant_proposals_mapping",
        lazy=LAZY_SELECTIN
    )
