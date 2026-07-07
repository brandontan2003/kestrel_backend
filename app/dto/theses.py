from decimal import Decimal
from typing import Any

from pydantic import field_validator

from app.dto.base import BaseDTO
from app.enums.ThesesEnum import QuantModeEnum, CatalystModeEnum, ThesesStatusEnum

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
    notes: str
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
    evidence: dict[str, Any] | None = None
    enabled: bool


class RetrieveThesesResponse(BaseDTO):
    theses_id: str
    user_id: str
    ticker: str
    theses_status: ThesesStatusEnum
    quant_mode: QuantModeEnum
    catalyst_mode: CatalystModeEnum
    notes: str
    quant_conditions: list[RetrieveQuantConditionResponse]
    catalysts: list[RetrieveCatalystResponse]
