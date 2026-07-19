import uuid
from typing import Optional

from sqlalchemy import Column, String, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import LAZY_SELECTIN, ModelName
from app.models.base import Base


class CatalystHistory(Base, Auditable):
    __tablename__ = "tbl_catalysts_history"

    catalyst_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    catalyst_id = Column(String(36), ForeignKey("tbl_catalysts.catalyst_id"), nullable=False)
    theses_id = Column(String(36), nullable=False)
    state = Column(String(15), nullable=False)
    description: Optional[str] = Column(String)
    evidence = Column(JSON)
    enabled = Column(Boolean, nullable=False)


@register_history(CatalystHistory)
class Catalyst(Base, Auditable):
    __tablename__ = "tbl_catalysts"

    catalyst_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theses_id = Column(String(36), ForeignKey("tbl_theses.theses_id"), nullable=False)
    state = Column(String(15), nullable=False)
    description: Optional[str] = Column(String)
    evidence = Column(JSON)
    enabled = Column(Boolean, default=True, nullable=False)

    theses_mapping = relationship(
        ModelName.THESES,
        back_populates="catalyst_mapping",
        lazy=LAZY_SELECTIN
    )
