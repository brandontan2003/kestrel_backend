import uuid

from sqlalchemy import Column, String, ForeignKey, Boolean, DECIMAL
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import LAZY_SELECTIN, ModelName
from app.models.base import Base


class QuantConditionHistory(Base, Auditable):
    __tablename__ = "tbl_quant_conditions_history"

    quant_condition_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quant_condition_id = Column(String(36), ForeignKey("tbl_quant_conditions.quant_condition_id"), nullable=False)
    theses_id = Column(String(36), nullable=False)
    metric = Column(String, nullable=False)
    operator = Column(String(2), nullable=False)
    value = Column(DECIMAL, nullable=False)
    enabled = Column(Boolean, nullable=False)


@register_history(QuantConditionHistory)
class QuantCondition(Base, Auditable):
    __tablename__ = "tbl_quant_conditions"

    quant_condition_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theses_id = Column(String(36), ForeignKey("tbl_theses.theses_id"), nullable=False)
    metric = Column(String, nullable=False)
    operator = Column(String(2), nullable=False)
    value = Column(DECIMAL, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    theses_mapping = relationship(
        ModelName.THESES,
        back_populates="quant_conditions_mapping",
        lazy=LAZY_SELECTIN
    )
