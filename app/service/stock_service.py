from fastapi import Depends

from app.dto.stock import RetrieveAllStockResponse
from app.repository.stock_repository import StockRepository, get_stock_repository


class StockService:
    def __init__(self, stock_repo: StockRepository):
        self._stock_repo = stock_repo

    async def retrieve_listed_stocks(self) -> RetrieveAllStockResponse:
        stocks = await self._stock_repo.get_all_stocks_with_listed_status()
        return RetrieveAllStockResponse(stocks=[stock.ticker for stock in stocks])


async def get_stock_service(stock_repo: StockRepository = Depends(get_stock_repository)) -> StockService:
    return StockService(stock_repo)
