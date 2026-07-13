from fastapi import APIRouter, Depends

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse, SuccessResponse
from app.dto.error import ErrorResponse
from app.dto.telegram import GenerateTokenResponse
from app.enums.ErrorEnum import ErrorEnum
from app.models.users import User
from app.service.telegram_service import TelegramService, get_telegram_service

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/connect", response_model=DataResponse[GenerateTokenResponse],
               responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                          422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                          })
async def generate_token(current_user: User = Depends(get_current_user), service: TelegramService = Depends(get_telegram_service)):
    return DataResponse(result=await service.generate_token(current_user))


@router.delete("/disconnect", response_model=SuccessResponse,
               responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                          422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                          })
async def disconnect_telegram(current_user: User = Depends(get_current_user), service: TelegramService = Depends(get_telegram_service)):
    return await service.disconnect(current_user)

@router.post("/webhook", response_model=SuccessResponse,
               responses={401: {"model": ErrorResponse, "description": ErrorEnum.INVALID_TOKEN_ERROR.error_code},
                          422: {"model": ErrorResponse, "description": ErrorEnum.VALIDATION_ERROR.error_code}
                          })
async def webhook(payload: dict, service: TelegramService = Depends(get_telegram_service)):
    await service.handle_webhook(payload);
    return SuccessResponse()