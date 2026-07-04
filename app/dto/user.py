from app.dto.base import BaseDTO


class UserProfileResponse(BaseDTO):
    user_id: str
    email: str
    username: str
    user_status: str
