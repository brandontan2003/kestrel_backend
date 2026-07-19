from datetime import datetime
from typing import Any

from app.dto.base import BaseDTO
from common.enums.AlertsEnum import AlertStatusEnum, AlertChannelsEnum


class EvaluationResponse(BaseDTO):
    evaluation_status: str
    prompt_version: str
    results: dict[str, Any]
    signal: str
    reason: str | None = None
    created_at: datetime


class RetrieveAlertResponse(BaseDTO):
    alert_id: str
    evaluation_id: str
    channels_sent: AlertChannelsEnum
    alert_status: AlertStatusEnum
    evaluation: EvaluationResponse


class RetrieveAllAlertResponse(BaseDTO):
    alerts: list[RetrieveAlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CreateAlertRequest(BaseDTO):
    evaluation_id: str
    user_id: str
    channels_sent: AlertChannelsEnum
