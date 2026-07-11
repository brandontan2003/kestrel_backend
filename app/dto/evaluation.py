from datetime import datetime
from typing import Any

from app.dto.base import BaseDTO


class EvaluationResponse(BaseDTO):
    evaluation_id: str
    evaluation_status: str
    prompt_version: str
    results: dict[str, Any]
    signal: str
    reason: str | None = None
    created_at: datetime


class RetrieveEvaluationResponse(BaseDTO):
    theses_id: str
    evaluation: EvaluationResponse
