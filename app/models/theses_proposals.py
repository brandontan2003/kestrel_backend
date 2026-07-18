import uuid

from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, DECIMAL, Text
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import LAZY_SELECTIN, ModelName
from app.models.base import Base
from common.enums.ProposalEnum import ProposalStatusEnum


class ThesesProposalHistory(Base, Auditable):
    __tablename__ = "tbl_theses_proposals_history"

    theses_proposal_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theses_proposal_id = Column(String(36), ForeignKey("tbl_theses_proposals.theses_proposal_id"), nullable=False)

    user_id = Column(String(36), nullable=False)
    stock_id = Column(String(36), nullable=False)
    proposed_change = Column(JSON, nullable=False)

    llm_rationale = Column(Text)
    llm_confidence = Column(DECIMAL(4, 3))

    source_article_url = Column(Text)
    source_evaluation_id = Column(String(36), nullable=False)
    theses_proposal_status = Column(String(15), nullable=False)
    rejection_reason = Column(Text)
    resolved_at = Column(DateTime(timezone=True))


@register_history(ThesesProposalHistory)
class ThesesProposal(Base, Auditable):
    __tablename__ = "tbl_theses_proposals"

    theses_proposal_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(String(36), ForeignKey("tbl_users.user_id"), nullable=False)
    stock_id = Column(String(36), ForeignKey("tbl_stocks.stock_id"), nullable=False)
    proposed_change = Column(JSON, nullable=False)

    llm_rationale = Column(Text)
    llm_confidence = Column(DECIMAL(4, 3))

    source_article_url = Column(Text)
    source_evaluation_id = Column(String(36), ForeignKey("tbl_evaluations.evaluation_id"), nullable=False)
    theses_proposal_status = Column(String(15), default=ProposalStatusEnum.PENDING, nullable=False)
    rejection_reason = Column(Text)
    resolved_at = Column(DateTime(timezone=True))

    evaluations_mapping = relationship(
        ModelName.EVALUATION,
        back_populates="theses_proposal_mapping",
        lazy=LAZY_SELECTIN
    )

    users_mapping = relationship(
        ModelName.USER,
        back_populates="theses_proposal_mapping",
        lazy=LAZY_SELECTIN
    )
