from fastapi import APIRouter, Depends

from app.core.authorization.auth_dependency import get_current_user
from app.dto.base import DataResponse
from app.dto.user import UserProfileResponse
from app.models.users import User
from app.service.user_service import build_user_response

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me", response_model=DataResponse[UserProfileResponse])
async def retrieve_current_user(current_user: User = Depends(get_current_user)):
    return DataResponse(result= await build_user_response(current_user))
