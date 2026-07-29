from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.database_dependency import get_db
from app.enums.StockEnum import StockStatusEnum
from app.models import Stock


class StockRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_stock_by_ticker(self, ticker: str) -> Stock | None:
        result = await self._db.execute(
            select(Stock).where(Stock.ticker == ticker)
        )
        stock = result.scalar_one_or_none()
        if stock:
            await self._db.refresh(stock)
        return stock

    async def get_stock_by_stock_id(self, stock_id: str) -> Stock | None:
        result = await self._db.execute(
            select(Stock).where(Stock.stock_id == stock_id)
        )
        stock = result.scalar_one_or_none()
        if stock:
            await self._db.refresh(stock)
        return stock

    async def create_stock(self, ticker: str) -> Stock:
        stock = Stock(ticker=ticker, stock_status=StockStatusEnum.LISTED)
        self._db.add(stock)
        await self._db.flush()
        await self._db.refresh(stock)
        return stock

    async def get_all_stocks_with_listed_status(self) -> list[Stock]:
        result = await self._db.execute(
            select(Stock).where(Stock.stock_status == StockStatusEnum.LISTED)
        )
        return list(result.scalars().all())


async def get_stock_repository(db: AsyncSession = Depends(get_db)) -> StockRepository:
    return StockRepository(db)
