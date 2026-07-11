from fastapi import APIRouter, Depends, Query

from app.core.authorization.auth_dependency import get_current_user
from app.dto.alert import RetrieveAllAlertResponse
from app.dto.base import DataResponse
from app.dto.error import ErrorResponse
from app.enums.ErrorEnum import ErrorEnum
from app.models import User
from app.service.alert_service import AlertService, get_alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=DataResponse[RetrieveAllAlertResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_all_alerts(
        page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
        current_user: User = Depends(get_current_user), service: AlertService = Depends(get_alert_service)):
    return DataResponse(
        result=await service.retrieve_all_alerts(user_id=current_user.user_id, page=page, page_size=page_size))


@router.get("/{alert_id}", response_model=DataResponse[RetrieveAllAlertResponse],
            responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                       404: {"model": ErrorResponse, "description": ErrorEnum.ALERT_NOT_FOUND.error_code},
                       422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                       })
async def retrieve_alert_by_alert_id(alert_id: str, current_user: User = Depends(get_current_user),
                                     service: AlertService = Depends(get_alert_service)):
    return DataResponse(result=await service.retrieve_alert_by_alert_id(alert_id, current_user.user_id))
