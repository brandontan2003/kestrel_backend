import uuid

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.AlertsEnum import AlertStatusEnum
from app.enums.SqlalchemyEnum import ModelName, LAZY_SELECTIN
from app.models.base import Base


class AlertHistory(Base, Auditable):
    __tablename__ = "tbl_alerts_history"

    alert_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("tbl_alerts.alert_id"), nullable=False)

    evaluation_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    channels_sent = Column(String(10), nullable=False)
    alert_status = Column(String(15), nullable=False)


@register_history(AlertHistory)
class Alert(Base, Auditable):
    __tablename__ = "tbl_alerts"

    alert_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("tbl_evaluations.evaluation_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("tbl_users.user_id"), nullable=False)
    channels_sent = Column(String(10), nullable=False)
    alert_status = Column(String(15), default=AlertStatusEnum.NOT_SENT, nullable=False)

    evaluations_mapping = relationship(
        ModelName.EVALUATION,
        back_populates="alerts_mapping",
        lazy=LAZY_SELECTIN
    )

    users_mapping = relationship(
        ModelName.USER,
        back_populates="alerts_mapping",
        lazy=LAZY_SELECTIN
    )
