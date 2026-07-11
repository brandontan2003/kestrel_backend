from fastapi import APIRouter, Depends, Query

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse, SuccessResponse
from app.dto.error import ErrorResponse
from app.dto.theses import CreateQuantConditionRequest, CreateThesesRequest, RetrieveThesesResponse, \
    CreateThesesResponse, RetrieveAllThesesResponse, UpdateThesesRequest, UpdateQuantConditionRequest, \
    CreateCatalystRequest, UpdateCatalystRequest, RetrieveAllEvaluationResponse
from app.enums.ErrorEnum import ErrorEnum
from app.models.users import User
from app.service.theses_service import ThesesService, get_theses_service

router = APIRouter(prefix="/theses", tags=["theses"])


@router.post("", response_model=DataResponse[CreateThesesResponse],
             responses={404: {"model": ErrorResponse, "description": ErrorEnum.STOCK_NOT_FOUND.error_code},
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
async def retrieve_all_theses(
        current_user: User = Depends(get_current_user), service: ThesesService = Depends(get_theses_service),
        page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    return DataResponse(result=await service.retrieve_all_theses(current_user.user_id, page, page_size))


@router.put("/{theses_id}", response_model=DataResponse[RetrieveThesesResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.THESES_NOT_FOUND.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def update_theses_by_theses_id(
        theses_id: str, payload: UpdateThesesRequest, current_user: User = Depends(get_current_user),
        service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.update_theses_by_theses_id(theses_id, current_user.user_id, payload))


@router.delete("/{theses_id}", response_model=SuccessResponse,
               responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                          404: {"model": ErrorResponse, "description": ErrorEnum.THESES_NOT_FOUND.error_code},
                          422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                          })
async def delete_theses(
        theses_id: str, current_user: User = Depends(get_current_user),
        service: ThesesService = Depends(get_theses_service)):
    return await service.delete_theses(theses_id, current_user.user_id)


# Quant Condition
@router.post("/{theses_id}/quant-condition", response_model=DataResponse[RetrieveThesesResponse],
             responses={404: {"model": ErrorResponse, "description": ErrorEnum.THESES_NOT_FOUND.error_code},
                        401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                        })
async def add_quant_condition_to_theses(
        theses_id: str, payload: CreateQuantConditionRequest, current_user: User = Depends(get_current_user),
        service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.add_quant_condition(theses_id, current_user.user_id, payload))


@router.put("/{theses_id}/quant-condition/{condition_id}", response_model=DataResponse[RetrieveThesesResponse],
            responses={404: {"model": ErrorResponse, "description": ErrorEnum.QUANT_CONDITION_NOT_FOUND.error_code},
                       401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def update_quant_condition(
        theses_id: str, condition_id: str, payload: UpdateQuantConditionRequest,
        current_user: User = Depends(get_current_user), service: ThesesService = Depends(get_theses_service)):
    return DataResponse(
        result=await service.update_quant_condition(theses_id, condition_id, current_user.user_id, payload))


@router.delete("/{theses_id}/quant-condition/{condition_id}", response_model=SuccessResponse,
               responses={404: {"model": ErrorResponse, "description": ErrorEnum.QUANT_CONDITION_NOT_FOUND.error_code},
                          401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                          422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                          })
async def delete_quant_condition(theses_id: str, condition_id: str, current_user: User = Depends(get_current_user),
                                 service: ThesesService = Depends(get_theses_service)):
    return await service.delete_quant_condition(theses_id, condition_id, current_user.user_id)


# Catalyst
@router.post("/{theses_id}/catalyst", response_model=DataResponse[RetrieveThesesResponse],
             responses={404: {"model": ErrorResponse, "description": ErrorEnum.THESES_NOT_FOUND.error_code},
                        401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                        422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                        })
async def add_catalyst_to_theses(
        theses_id: str, payload: CreateCatalystRequest, current_user: User = Depends(get_current_user),
        service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.add_catalyst(theses_id, current_user.user_id, payload))


@router.put("/{theses_id}/catalyst/{catalyst_id}", response_model=DataResponse[RetrieveThesesResponse],
            responses={404: {"model": ErrorResponse, "description": ErrorEnum.CATALYST_NOT_FOUND.error_code},
                       401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def update_catalyst(
        theses_id: str, catalyst_id: str, payload: UpdateCatalystRequest,
        current_user: User = Depends(get_current_user), service: ThesesService = Depends(get_theses_service)):
    return DataResponse(
        result=await service.update_catalyst(theses_id, catalyst_id, current_user.user_id, payload))


@router.delete("/{theses_id}/catalyst/{catalyst_id}", response_model=SuccessResponse,
               responses={404: {"model": ErrorResponse, "description": ErrorEnum.CATALYST_NOT_FOUND.error_code},
                          401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                          422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                          })
async def delete_catalyst(theses_id: str, catalyst_id: str, current_user: User = Depends(get_current_user),
                          service: ThesesService = Depends(get_theses_service)):
    return await service.delete_catalyst(theses_id, catalyst_id, current_user.user_id)


# Evaluation
@router.get("/{theses_id}/evaluations", response_model=DataResponse[RetrieveAllEvaluationResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.THESES_NOT_FOUND.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_evaluations_by_theses_id(
        theses_id: str, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
        current_user: User = Depends(get_current_user), service: ThesesService = Depends(get_theses_service)):
    return DataResponse(
        result=await service.retrieve_evaluations_by_theses_id(theses_id, current_user.user_id, page, page_size))
