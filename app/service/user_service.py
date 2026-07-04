from fastapi import Depends

from app.dto.user import UserProfileResponse
from app.models.users import User
from app.repository.user_repository import UserRepository, get_user_repository


async def build_user_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=user.user_id,
        email=user.email,
        username=user.username,
        user_status=user.user_status
    )


class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo


async def get_user_service(user_repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(user_repo)
