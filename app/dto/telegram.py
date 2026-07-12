from datetime import datetime

from app.dto.base import BaseDTO


class UpdateTelegramDetailRequest(BaseDTO):
    chat_id: str | None = None
    token: str | None = None
    expires_at: datetime | None = None


class GenerateTokenResponse(BaseDTO):
    token: str
    expires_in_seconds: int
    instruction: str
    unique_link: str
    