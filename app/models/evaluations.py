import uuid
from typing import Optional

from sqlalchemy import Column, String, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import ModelName, LAZY_SELECTIN, RelationshipCascade
from app.models.base import Base


class EvaluationHistory(Base, Auditable):
    __tablename__ = "tbl_evaluations_history"

    evaluation_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("tbl_evaluations.evaluation_id"), nullable=False)
    theses_id = Column(String(36), nullable=False)
    evaluation_status = Column(String(15), nullable=False)
    prompt_version = Column(String, nullable=False)
    results = Column(JSON, nullable=False)
    signal = Column(Boolean, nullable=False)
    reason: Optional[str] = Column(String)


@register_history(EvaluationHistory)
class Evaluation(Base, Auditable):
    __tablename__ = "tbl_evaluations"

    evaluation_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theses_id = Column(String(36), ForeignKey("tbl_theses.theses_id"), nullable=False)
    evaluation_status = Column(String(15), nullable=False)
    prompt_version = Column(String, nullable=False)
    results = Column(JSON, nullable=False)
    signal = Column(Boolean, default=True, nullable=False)
    reason: Optional[str] = Column(String)

    theses_mapping = relationship(
        ModelName.THESES,
        back_populates="evaluations_mapping",
        lazy=LAZY_SELECTIN
    )

    alerts_mapping = relationship(
        ModelName.ALERT,
        back_populates="evaluations_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    theses_proposal_mapping = relationship(
        ModelName.THESES_PROPOSAL,
        back_populates="evaluations_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    catalyst_proposals_mapping = relationship(
        ModelName.CATALYST_PROPOSAL,
        back_populates="evaluations_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    quant_proposals_mapping = relationship(
        ModelName.QUANT_PROPOSAL,
        back_populates="evaluations_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )
