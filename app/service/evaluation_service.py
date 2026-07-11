from fastapi import Depends

from app.dto.evaluation import RetrieveEvaluationResponse, EvaluationResponse
from app.exception_handler import EvaluationNotFoundException
from app.repository.evaluation_repository import EvaluationRepository, get_evaluation_repository


class EvaluationService:
    def __init__(self, eval_repo: EvaluationRepository):
        self._evaluation_repo = eval_repo

    async def get_evaluation(self, evaluation_id: str, user_id: str) -> RetrieveEvaluationResponse:
        evaluation = await self._evaluation_repo.get_evaluation_by_evaluation_id_and_user_id(evaluation_id, user_id)
        if evaluation is None:
            raise EvaluationNotFoundException()
        result = EvaluationResponse(**evaluation.__dict__)
        return RetrieveEvaluationResponse(theses_id=evaluation.theses_id, evaluation=result)


async def get_evaluation_service(
        eval_repo: EvaluationRepository = Depends(get_evaluation_repository)) -> EvaluationService:
    return EvaluationService(eval_repo)
