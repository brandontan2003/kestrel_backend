from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey
from sqlalchemy.sql import func

from app.models.base import Base


@register_history(UserHistory)
class User(Base, Auditable):
    __tablename__ = "tbl_users"

    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    user_status = Column(String(10), default=UserStatusEnum.ACTIVE, server_default=UserStatusEnum.ACTIVE, nullable=False)


class UserHistory(Base, Auditable):
    __tablename__ = "tbl_users_history"

    user_history_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("tbl_users.user_id"), nullable=False)
    email = Column(String, nullable=False)
    username = Column(String, nullable=False)
    user_status = Column(String, nullable=False)
    