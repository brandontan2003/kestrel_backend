from fastapi import APIRouter, Depends

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse
from app.dto.theses import CreateThesesRequest, RetrieveThesesResponse
from app.models.users import User
from app.service.theses_service import ThesesService, get_theses_service

router = APIRouter(prefix="/theses", tags=["theses"])


@router.post("", response_model=DataResponse[RetrieveThesesResponse])
async def create_theses(payload: CreateThesesRequest, current_user: User = Depends(get_current_user),
                        service: ThesesService = Depends(get_theses_service)):
    return DataResponse(result=await service.create_theses(current_user.user_id, payload))
