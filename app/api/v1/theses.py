from fastapi import APIRouter, Depends

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse
from app.dto.error import ErrorResponse
from app.enums.ErrorEnum import ErrorEnum
from app.dto.theses import CreateThesesRequest, RetrieveThesesResponse
from app.models.users import User
from app.service.theses_service import ThesesService, get_theses_service

router = APIRouter(prefix="/theses", tags=["theses"])


@router.post("", response_model=DataResponse[RetrieveThesesResponse], 
             responses={400: {"model": ErrorResponse, "description": ErrorEnum.STOCK_NOT_FOUND.error_code},
                        401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                        })
async def create_theses(payload: CreateThesesRequest, current_user: User = Depends(get_current_user),
                        service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.create_theses(current_user.user_id, payload))

@router.post("/{theses_id}", response_model=DataResponse[RetrieveThesesResponse],
             responses={400: {"model": ErrorResponse, "description": ErrorEnum.THESES_NOT_FOUND.error_code},
                        401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                        })
async def retrieve_theses_by_theses_id(theses_id: str, current_user: User = Depends(get_current_user), service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.retrieve_theses_by_theses_id(theses_id, current_user.user_id))
