from datetime import datetime, timedelta, timezone
import uuid

from fastapi import Depends

from app.dto.telegram import GenerateTokenResponse, UpdateTelegramDetailRequest
from app.models.users import User
from app.repository.user_repository import UserRepository, get_user_repository
from app.config import settings


class TelegramService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def generate_token(self, user: User) -> GenerateTokenResponse:
        token = str(uuid.uuid4())
        token_ttl_seconds = settings.TOKEN_TTL_SECONDS
        telegram_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_ttl_seconds)
        
        request = UpdateTelegramDetailRequest(token=token, expires_at=telegram_token_expires_at)
        await self._user_repo.update_user_telegram_details(user, request)

        return GenerateTokenResponse(
            token=token,
            expires_in_seconds=token_ttl_seconds,
            instruction=f"Send `/authorize {token}` to @KestrelFinanceBot",
            unique_link=f"={settings.TELEGRAM_BOT_URL}/?text=/authorize%20{token}"
        )

async def get_telegram_service(user_repo: UserRepository = Depends(get_user_repository)) -> TelegramService:
    return TelegramService(user_repo)
