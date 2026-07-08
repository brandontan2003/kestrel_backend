from fastapi import APIRouter, Depends, Query

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse
from app.dto.error import ErrorResponse
from app.enums.ErrorEnum import ErrorEnum
from app.dto.theses import CreateThesesRequest, RetrieveThesesResponse, CreateThesesResponse, RetrieveAllThesesResponse
from app.models.users import User
from app.service.theses_service import ThesesService, get_theses_service

router = APIRouter(prefix="/theses", tags=["theses"])


@router.post("", response_model=DataResponse[CreateThesesResponse], 
             responses={400: {"model": ErrorResponse, "description": ErrorEnum.STOCK_NOT_FOUND.error_code},
                        401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                        })
async def create_theses(payload: CreateThesesRequest, current_user: User = Depends(get_current_user),
                        service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.create_theses(current_user.user_id, payload))

@router.get("/{theses_id}", response_model=DataResponse[RetrieveThesesResponse],
             responses={404: {"model": ErrorResponse, "description": ErrorEnum.THESES_NOT_FOUND.error_code},
                        401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                        })
async def retrieve_theses_by_theses_id(theses_id: str, current_user: User = Depends(get_current_user), 
                                       service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.retrieve_theses_by_theses_id(theses_id, current_user.user_id))


@router.get("", response_model=DataResponse[RetrieveAllThesesResponse],
             responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                        })
async def retrieve_all_theses(current_user: User = Depends(get_current_user), service: ThesesService = Depends(get_theses_service), 
                              page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),):
    return DataResponse(result=await service.retrieve_all_theses(current_user.user_id, page, page_size))
