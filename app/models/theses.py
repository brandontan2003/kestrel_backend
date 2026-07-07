import uuid

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import LAZY_SELECTIN, RelationshipCascade, ModelName
from app.enums.ThesesEnum import ThesesStatusEnum, QuantModeEnum, CatalystModeEnum
from app.models.base import Base


class ThesesHistory(Base, Auditable):
    __tablename__ = "tbl_theses_history"

    theses_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    theses_id = Column(String(36), ForeignKey("tbl_theses.theses_id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    stock_id = Column(String(36), nullable=False)
    theses_status = Column(String(10), nullable=False)
    quant_mode = Column(String(10), nullable=False)
    catalyst_mode = Column(String(10), nullable=False)
    notes = Column(String, nullable=False)


@register_history(ThesesHistory)
class Theses(Base, Auditable):
    __tablename__ = "tbl_theses"

    theses_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("tbl_users.user_id"), nullable=False)
    stock_id = Column(String(36), ForeignKey("tbl_stocks.stock_id"), nullable=False)
    theses_status = Column(String(10), default=ThesesStatusEnum.TRACKING, nullable=False)
    quant_mode = Column(String(10), default=QuantModeEnum.ANY, nullable=False)
    catalyst_mode = Column(String(10), default=CatalystModeEnum.ANY, nullable=False)
    notes = Column(String, nullable=False)

    users_mapping = relationship(
        ModelName.USER,
        back_populates="theses_mapping",
        lazy=LAZY_SELECTIN
    )

    quant_conditions_mapping = relationship(
        ModelName.QUANT_CONDITION,
        back_populates="theses_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    catalyst_mapping = relationship(
        ModelName.CATALYST,
        back_populates="theses_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    evaluations_mapping = relationship(
        ModelName.EVALUATION,
        back_populates="theses_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    outcomes_mapping = relationship(
        ModelName.OUTCOME,
        back_populates="theses_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    catalyst_proposals_mapping = relationship(
        ModelName.CATALYST_PROPOSAL,
        back_populates="theses_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    quant_proposals_mapping = relationship(
        ModelName.QUANT_PROPOSAL,
        back_populates="theses_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )
