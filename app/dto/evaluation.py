from typing import Any

from pydantic import BaseModel


class RetrieveEvaluationResponse(BaseModel):
    evaluation_id: str
    theses_id: str
    evaluation_status: str
    prompt_version: str
    results: dict[str, Any]
    signal: str
    reason: str | None
