import uuid

from sqlalchemy import Column, String, ForeignKey

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.UserEnum import UserStatusEnum
from app.models.base import Base


class UserHistory(Base, Auditable):
    __tablename__ = "tbl_users_history"

    user_history_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("tbl_users.user_id"), nullable=False)
    email = Column(String, nullable=False)
    username = Column(String, nullable=False)
    user_status = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)


@register_history(UserHistory)
class User(Base, Auditable):
    __tablename__ = "tbl_users"

    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    user_status = Column(String(10), default=UserStatusEnum.ACTIVE, nullable=False)
    password_hash = Column(String, nullable=False)
