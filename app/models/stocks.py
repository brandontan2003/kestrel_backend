import uuid

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database.auditable import Auditable
from app.core.database.history_decorator import register_history
from app.enums.StockEnum import StockStatusEnum
from app.enums.SqlalchemyEnum import LAZY_SELECTIN, RelationshipCascade, ModelName
from app.models.base import Base


class StockHistory(Base, Auditable):
    __tablename__ = "tbl_stocks_history"

    stock_history_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    stock_id = Column(String, ForeignKey("tbl_stocks.stock_id"), nullable=False)
    ticker = Column(String(30), unique=True, nullable=False)
    stock_status = Column(String(10), nullable=False)


@register_history(StockHistory)
class Stock(Base, Auditable):
    __tablename__ = "tbl_stocks"

    stock_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker = Column(String(30), unique=True, nullable=False)
    stock_status = Column(String(10), default=StockStatusEnum.LISTED, nullable=False)

    theses_mapping = relationship(
        ModelName.THESES,
        back_populates="stocks_mapping",
        cascade=RelationshipCascade.DELETE_ORPHAN,
        lazy=LAZY_SELECTIN
    )