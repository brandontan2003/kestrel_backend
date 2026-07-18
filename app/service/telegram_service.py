import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from telegram import Bot

from app.config import settings
from app.core.logger import logger
from app.dto.base import SuccessResponse
from app.dto.telegram import GenerateTokenResponse, UpdateTelegramDetailRequest
from app.models.users import User
from app.repository.user_repository import UserRepository, get_user_repository

_bot: Bot | None = None


def _get_bot() -> Bot | None:
    """Construct the Telegram Bot lazily and cache it.

    Building it at import time meant the whole app crashed on startup whenever
    TELEGRAM_BOT_TOKEN was unset (fresh clones, CI, tests). Deferring it here lets
    the app import and run without Telegram configured — the feature just no-ops
    (returns None) until a token is provided.
    """
    global _bot
    if _bot is None and settings.TELEGRAM_BOT_TOKEN:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


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
            unique_link=f"{settings.TELEGRAM_BOT_URL}/?text=/authorize%20{token}"
        )

    async def disconnect(self, user: User) -> SuccessResponse:
        await self._user_repo.update_user_telegram_details(user, UpdateTelegramDetailRequest())
        return SuccessResponse()

    async def handle_webhook(self, payload: dict) -> None:
        message = payload.get("message", {})
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id")

        if not text.startswith("/authorize") or not chat_id:
            return  # ignore anything that isn't a /authorize command or doesn't have a chat_id

        parts = text.split()
        if len(parts) != 2:
            await self._safe_send(chat_id=chat_id, text="Send this from the Kestrel app — Settings → Connect Telegram.")
            return

        token = parts[1]
        user = await self._user_repo.get_by_not_expired_telegram_token(token)

        if not user:
            await self._safe_send(chat_id=chat_id,
                                  text="This link has expired or is invalid. Generate a new one from Kestrel.")
            return

        request = UpdateTelegramDetailRequest(chat_id=str(chat_id))
        await self._user_repo.update_user_telegram_details(user, request)

        await self._safe_send(chat_id=chat_id, text="✅ Kestrel connected. You'll receive alerts here.")
        logger.info(f"Telegram linked for user {user.user_id}, chat_id={chat_id}")

    async def _safe_send(self, chat_id: int, text: str) -> None:
        bot = _get_bot()
        if bot is None:
            logger.warning("Telegram not configured (TELEGRAM_BOT_TOKEN unset); skipping message to %s", chat_id)
            return
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.error(f"Telegram send failed to {chat_id}: {e}")


async def get_telegram_service(user_repo: UserRepository = Depends(get_user_repository)) -> TelegramService:
    return TelegramService(user_repo)
