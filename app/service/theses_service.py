# app/service/theses_service.py

from fastapi import Depends

from app.dto.theses import CreateThesesRequest, RetrieveThesesResponse
from app.exception_handler import StockNotFoundException, ThesesFoundException
from app.models import Theses
from app.repository.catalyst_repository import CatalystRepository, get_catalyst_repository
from app.repository.quant_condition_repository import QuantConditionRepository, get_quant_condition_repository
from app.repository.stock_repository import StockRepository, get_stock_repository
from app.repository.theses_repository import ThesesRepository, get_theses_repository


class ThesesService:
    def __init__(self, theses_repo: ThesesRepository, stock_repo: StockRepository,
                 quant_condition_repo: QuantConditionRepository, catalyst_repo: CatalystRepository):
        self._theses_repo = theses_repo
        self._stock_repo = stock_repo
        self._quant_condition_repo = quant_condition_repo
        self._catalyst_repo = catalyst_repo

    async def retrieve_theses_by_theses_id(self, theses_id: str, user_id: str) -> RetrieveThesesResponse:
        theses = await self._theses_repo.get_theses_by_theses_id(theses_id)
        if theses is None or theses.user_id != user_id:
            raise ThesesFoundException()
        return RetrieveThesesResponse(
            **theses.__dict__,
            ticker=theses.stocks_mapping.ticker,
            quant_conditions=theses.quant_conditions_mapping,
            catalysts=theses.catalyst_mapping
            )

    async def create_theses(self, user_id: str, request: CreateThesesRequest) -> RetrieveThesesResponse:
        stock = await self._stock_repo.get_stock_by_ticker(request.ticker)
        if stock is None:
            raise StockNotFoundException()

        theses = await self._theses_repo.create_theses(
            user_id=user_id,
            stock_id=stock.stock_id,
            quant_mode=request.quant_mode,
            catalyst_mode=request.catalyst_mode,
            notes=request.notes,
        )

        theses_id = theses.theses_id

        quant_conditions = request.quant_conditions
        if quant_conditions:
            await self._quant_condition_repo.bulk_create_quant_condition(theses_id=theses_id, quant_conditions=quant_conditions)

        catalysts = request.catalysts
        if catalysts:
            await self._catalyst_repo.bulk_create_catalysts(theses_id=theses_id, catalysts=catalysts)
        
        return await self.retrieve_theses_by_theses_id(theses_id, user_id)


async def get_theses_service(
        theses_repo: ThesesRepository = Depends(get_theses_repository),
        stock_repo: StockRepository = Depends(get_stock_repository),
        quant_condition_repo: QuantConditionRepository = Depends(get_quant_condition_repository),
        catalyst_repo: CatalystRepository = Depends(get_catalyst_repository)
) -> ThesesService:
    return ThesesService(theses_repo, stock_repo, quant_condition_repo, catalyst_repo)
