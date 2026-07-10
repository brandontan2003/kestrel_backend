import uuid

from sqlalchemy import Column, String, ForeignKey, DateTime, DECIMAL
from sqlalchemy.dialects.postgresql import MONEY
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import LAZY_SELECTIN, ModelName
from app.models.base import Base


class OutcomeHistory(Base, Auditable):
    __tablename__ = "tbl_outcomes_history"

    outcome_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    outcome_id = Column(String(36), ForeignKey("tbl_outcomes.outcome_id"), nullable=False)
    theses_id = Column(String(36), nullable=False)
    price_at_signal = Column(MONEY, nullable=False)
    llm_confidence = Column(DECIMAL(4, 3), nullable=False)
    triggered_at = Column(DateTime(timezone=True))
    price_after_30d = Column(MONEY)
    notes = Column(String)


@register_history(OutcomeHistory)
class Outcome(Base, Auditable):
    __tablename__ = "tbl_outcomes"

    outcome_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theses_id = Column(String(36), ForeignKey("tbl_theses.theses_id"), nullable=False)
    price_at_signal = Column(MONEY, nullable=False)
    llm_confidence = Column(DECIMAL(4, 3), nullable=False)
    triggered_at = Column(DateTime(timezone=True))
    price_after_30d = Column(MONEY)
    notes = Column(String)

    theses_mapping = relationship(
        ModelName.THESES,
        back_populates="outcomes_mapping",
        lazy=LAZY_SELECTIN
    )
