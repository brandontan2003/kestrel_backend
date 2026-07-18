from decimal import Decimal
from typing import Any

from pydantic import field_validator

from app.dto.base import BaseDTO
from app.dto.evaluation import EvaluationResponse
from common.enums.ThesesEnum import QuantModeEnum, CatalystModeEnum, ThesesStatusEnum

VALID_OPERATORS = {"<", ">", "<=", ">=", "=="}


class QuantConditionRequest(BaseDTO):
    metric: str
    operator: str
    value: Decimal

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            raise ValueError(f"Operator must be one of {VALID_OPERATORS}")
        return v


class CatalystRequest(BaseDTO):
    state: str
    description: str | None = None
    evidence: dict[str, Any] | None = None


class CreateThesesRequest(BaseDTO):
    ticker: str
    quant_mode: QuantModeEnum
    catalyst_mode: CatalystModeEnum
    notes: str | None = None
    quant_conditions: list[QuantConditionRequest]
    catalysts: list[CatalystRequest]


class RetrieveQuantConditionResponse(BaseDTO):
    quant_condition_id: str
    metric: str
    operator: str
    value: Decimal
    enabled: bool


class RetrieveCatalystResponse(BaseDTO):
    catalyst_id: str
    state: str
    description: str | None = None
    # The ML pipeline persists evidence as an append-only LIST of verdict entries;
    # a plain dict is also tolerated for hand-authored/legacy rows.
    evidence: list[dict[str, Any]] | dict[str, Any] | None = None
    enabled: bool


class CreateThesesResponse(BaseDTO):
    theses_id: str
    ticker: str
    theses_status: ThesesStatusEnum
    quant_mode: QuantModeEnum
    catalyst_mode: CatalystModeEnum
    notes: str | None = None
    quant_conditions: list[RetrieveQuantConditionResponse]
    catalysts: list[RetrieveCatalystResponse]


class ThesesResponse(BaseDTO):
    theses_id: str
    ticker: str
    theses_status: ThesesStatusEnum
    quant_mode: QuantModeEnum
    catalyst_mode: CatalystModeEnum
    notes: str | None = None
    quant_conditions: list[RetrieveQuantConditionResponse]
    catalysts: list[RetrieveCatalystResponse]
    latest_evaluation: EvaluationResponse | None = None


class RetrieveThesesResponse(BaseDTO):
    user_id: str
    theses: ThesesResponse


class RetrieveAllThesesResponse(BaseDTO):
    user_id: str
    theses: list[ThesesResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UpdateThesesRequest(BaseDTO):
    theses_status: ThesesStatusEnum | None = None
    quant_mode: QuantModeEnum | None = None
    catalyst_mode: CatalystModeEnum | None = None
    notes: str | None = None


class CreateQuantConditionRequest(BaseDTO):
    metric: str
    operator: str
    value: Decimal

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            raise ValueError(f"Operator must be one of {VALID_OPERATORS}")
        return v


class UpdateQuantConditionRequest(BaseDTO):
    metric: str | None = None
    operator: str | None = None
    value: Decimal | None = None
    enabled: bool | None = None

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            raise ValueError(f"Operator must be one of {VALID_OPERATORS}")
        return v


class UpdateCatalystRequest(BaseDTO):
    state: str | None = None
    description: str | None = None
    evidence: dict[str, Any] | None = None
    enabled: bool | None = None


class CreateCatalystRequest(BaseDTO):
    state: str
    description: str | None = None
    evidence: dict[str, Any] | None = None


class RetrieveAllEvaluationResponse(BaseDTO):
    theses_id: str
    evaluations: list[EvaluationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
