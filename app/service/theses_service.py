from fastapi import Depends

from app.dto.base import SuccessResponse
from app.dto.evaluation import EvaluationResponse
from app.dto.theses import CreateQuantConditionRequest, CreateThesesRequest, RetrieveThesesResponse, \
    CreateThesesResponse, RetrieveAllThesesResponse, UpdateThesesRequest, UpdateQuantConditionRequest, \
    CreateCatalystRequest, UpdateCatalystRequest, RetrieveAllEvaluationResponse
from app.exception_handler import QuantConditionNotFoundException, StockNotFoundException, ThesesNotFoundException, \
    CatalystNotFoundException
from app.repository.catalyst_repository import CatalystRepository, get_catalyst_repository
from app.repository.evaluation_repository import EvaluationRepository, get_evaluation_repository
from app.repository.quant_condition_repository import QuantConditionRepository, get_quant_condition_repository
from app.repository.stock_repository import StockRepository, get_stock_repository
from app.repository.theses_repository import ThesesRepository, get_theses_repository


class ThesesService:
    def __init__(self, theses_repo: ThesesRepository, stock_repo: StockRepository,
                 quant_condition_repo: QuantConditionRepository, catalyst_repo: CatalystRepository,
                 evaluation_repo: EvaluationRepository):
        self._theses_repo = theses_repo
        self._stock_repo = stock_repo
        self._quant_condition_repo = quant_condition_repo
        self._catalyst_repo = catalyst_repo
        self._evaluation_repo = evaluation_repo

    async def delete_theses(self, theses_id: str, user_id: str) -> SuccessResponse:
        theses = await self._theses_repo.get_theses_by_theses_id(theses_id)
        if theses is None or theses.user_id != user_id:
            raise ThesesNotFoundException()

        await self._theses_repo.delete_theses(theses)
        return SuccessResponse()

    async def update_theses_by_theses_id(self, theses_id: str, user_id: str,
                                         request: UpdateThesesRequest) -> RetrieveThesesResponse:
        theses = await self._theses_repo.get_theses_by_theses_id(theses_id)
        if theses is None or theses.user_id != user_id:
            raise ThesesNotFoundException()

        updated_theses = await self._theses_repo.update_theses(theses, request)
        latest_evaluation = await self._evaluation_repo.get_latest_evaluation(theses_id)

        return RetrieveThesesResponse(
            **updated_theses.__dict__,
            ticker=updated_theses.stocks_mapping.ticker,
            quant_conditions=updated_theses.quant_conditions_mapping,
            catalysts=updated_theses.catalyst_mapping,
            latest_evaluation=latest_evaluation,
        )

    async def retrieve_all_theses(self, user_id: str, page: int, page_size: int) -> RetrieveAllThesesResponse:
        all_theses, total = await self._theses_repo.get_all_theses_by_user_id(user_id, page, page_size)

        theses_ids = [t.theses_id for t in all_theses]
        evaluations_by_theses_id = await self._evaluation_repo.get_latest_evaluations_by_user_id(theses_ids)
        result = [
            RetrieveThesesResponse(
                **theses.__dict__,
                ticker=theses.stocks_mapping.ticker,
                quant_conditions=theses.quant_conditions_mapping,
                catalysts=theses.catalyst_mapping,
                latest_evaluation=evaluations_by_theses_id.get(theses.theses_id),
            )
            for theses in all_theses
        ]

        return RetrieveAllThesesResponse(theses=result, total=total, page=page, page_size=page_size,
                                         total_pages=-(-total // page_size))

    async def retrieve_theses_by_theses_id(self, theses_id: str, user_id: str) -> RetrieveThesesResponse:
        theses = await self._theses_repo.get_theses_by_theses_id(theses_id)
        if theses is None or theses.user_id != user_id:
            raise ThesesNotFoundException()

        latest_evaluation = await self._evaluation_repo.get_latest_evaluation(theses_id)

        return RetrieveThesesResponse(
            **theses.__dict__,
            ticker=theses.stocks_mapping.ticker,
            quant_conditions=theses.quant_conditions_mapping,
            catalysts=theses.catalyst_mapping,
            latest_evaluation=latest_evaluation
        )

    async def create_theses(self, user_id: str, request: CreateThesesRequest) -> CreateThesesResponse:
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
            await self._quant_condition_repo.bulk_create_quant_condition(theses_id=theses_id,
                                                                         quant_conditions=quant_conditions)

        catalysts = request.catalysts
        if catalysts:
            await self._catalyst_repo.bulk_create_catalysts(theses_id=theses_id, catalysts=catalysts)

        await self._theses_repo.expire_theses(theses)
        query_theses = await self._theses_repo.get_theses_by_theses_id(theses_id)

        return CreateThesesResponse(
            **query_theses.__dict__,
            ticker=query_theses.stocks_mapping.ticker,
            quant_conditions=query_theses.quant_conditions_mapping,
            catalysts=query_theses.catalyst_mapping
        )

    async def add_quant_condition(self, theses_id: str, user_id: str,
                                  request: CreateQuantConditionRequest) -> RetrieveThesesResponse:
        theses = await self._theses_repo.get_theses_by_theses_id(theses_id)
        if theses is None or theses.user_id != user_id:
            raise ThesesNotFoundException()

        await self._quant_condition_repo.create_quant_condition(
            theses_id=theses_id,
            metric=request.metric,
            operator=request.operator,
            value=request.value
        )
        await self._theses_repo.expire_theses(theses)
        return await self.retrieve_theses_by_theses_id(theses_id, user_id)

    async def update_quant_condition(self, theses_id: str, condition_id: str, user_id: str,
                                     payload: UpdateQuantConditionRequest) -> RetrieveThesesResponse:
        condition = await self._quant_condition_repo.get_quant_condition_by_id_and_user(
            condition_id, theses_id, user_id)
        if condition is None:
            raise QuantConditionNotFoundException()

        await self._quant_condition_repo.update_quant_condition(condition, payload)
        return await self.retrieve_theses_by_theses_id(theses_id, user_id)

    async def delete_quant_condition(self, theses_id: str, condition_id: str, user_id: str) -> SuccessResponse:
        quant_condition = await self._quant_condition_repo.get_quant_condition_by_id_and_user(condition_id, theses_id,
                                                                                              user_id)
        if quant_condition is None:
            raise QuantConditionNotFoundException()

        await self._quant_condition_repo.delete_quant_condition(quant_condition)
        return SuccessResponse()

    async def add_catalyst(self, theses_id: str, user_id: str,
                           request: CreateCatalystRequest) -> RetrieveThesesResponse:
        theses = await self._theses_repo.get_theses_by_theses_id(theses_id)
        if theses is None or theses.user_id != user_id:
            raise ThesesNotFoundException()

        await self._catalyst_repo.create_catalyst(
            theses_id=theses_id,
            state=request.state,
            description=request.description,
            evidence=request.evidence
        )
        await self._theses_repo.expire_theses(theses)
        return await self.retrieve_theses_by_theses_id(theses_id, user_id)

    async def update_catalyst(self, theses_id: str, catalyst_id: str, user_id: str,
                              payload: UpdateCatalystRequest) -> RetrieveThesesResponse:
        catalyst = await self._catalyst_repo.get_catalyst_by_id_and_user(catalyst_id, theses_id, user_id)
        if catalyst is None:
            raise CatalystNotFoundException()

        await self._catalyst_repo.update_catalyst(catalyst, payload)
        return await self.retrieve_theses_by_theses_id(theses_id, user_id)

    async def delete_catalyst(self, theses_id: str, catalyst_id: str, user_id: str) -> SuccessResponse:
        catalyst = await self._catalyst_repo.get_catalyst_by_id_and_user(catalyst_id, theses_id, user_id)
        if catalyst is None:
            raise CatalystNotFoundException()

        await self._catalyst_repo.delete_catalyst(catalyst)
        return SuccessResponse()

    async def retrieve_evaluations_by_theses_id(self, theses_id: str, user_id: str, page: int,
                                                page_size: int) -> RetrieveAllEvaluationResponse:
        theses = await self._theses_repo.get_theses_by_theses_id_and_user_id(theses_id, user_id)
        if theses is None:
            raise ThesesNotFoundException()

        evaluations, total = await self._evaluation_repo.get_all_evaluation_by_theses_id(theses_id, page, page_size)
        result = [EvaluationResponse(**evaluation.__dict__) for evaluation in evaluations]
        return RetrieveAllEvaluationResponse(theses_id=theses_id, evaluations=result, total=total, page=page,
                                             page_size=page_size, total_pages=-(-total // page_size))


async def get_theses_service(
        theses_repo: ThesesRepository = Depends(get_theses_repository),
        stock_repo: StockRepository = Depends(get_stock_repository),
        quant_condition_repo: QuantConditionRepository = Depends(get_quant_condition_repository),
        catalyst_repo: CatalystRepository = Depends(get_catalyst_repository),
        evaluation_repo: EvaluationRepository = Depends(get_evaluation_repository)
) -> ThesesService:
    return ThesesService(theses_repo, stock_repo, quant_condition_repo, catalyst_repo, evaluation_repo)
