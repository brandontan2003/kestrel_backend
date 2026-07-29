from fastapi import APIRouter, Depends

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse
from app.dto.error import ErrorResponse
from app.dto.evaluation import RetrieveEvaluationResponse
from app.enums.ErrorEnum import ErrorEnum
from app.models import User
from app.service.evaluation_service import EvaluationService, get_evaluation_service

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/{evaluation_id}", response_model=DataResponse[RetrieveEvaluationResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.EVALUATION_NOT_FOUND.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_evaluation_by_evaluation_id(
        evaluation_id: str, current_user: User = Depends(get_current_user),
        service: EvaluationService = Depends(get_evaluation_service)):
    return DataResponse(
        result=await service.get_evaluation(evaluation_id=evaluation_id, user_id=current_user.user_id))
