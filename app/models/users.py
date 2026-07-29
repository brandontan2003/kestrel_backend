import uuid

from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.SqlalchemyEnum import RelationshipCascade, ModelName, LAZY_SELECTIN
from app.enums.UserEnum import UserStatusEnum
from app.models.base import Base


class UserHistory(Base, Auditable):
    __tablename__ = "tbl_users_history"

    user_history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("tbl_users.user_id"), nullable=False)
    email = Column(String, nullable=False)
    username = Column(String, nullable=False)
    user_status = Column(String(10), nullable=False)
    password_hash = Column(String, nullable=False)
    telegram_chat_id = Column(String, nullable=True)
    telegram_handle = Column(String, nullable=True)
    telegram_link_token = Column(String(36), nullable=True)
    telegram_token_expires_at = Column(DateTime(timezone=True), nullable=True)


@register_history(UserHistory)
class User(Base, Auditable):
    __tablename__ = "tbl_users"

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    user_status = Column(String(10), default=UserStatusEnum.ACTIVE, nullable=False)
    password_hash = Column(String, nullable=False)
    telegram_chat_id = Column(String, nullable=True)
    telegram_handle = Column(String, nullable=True)
    telegram_link_token = Column(String(36), nullable=True)
    telegram_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    alerts_mapping = relationship(
        ModelName.ALERT,
        back_populates="users_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    theses_mapping = relationship(
        ModelName.THESES,
        back_populates="users_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )

    theses_proposal_mapping = relationship(
        ModelName.THESES_PROPOSAL,
        back_populates="users_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )
