from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.dto.base import BaseDTO


class RejectProposalRequest(BaseDTO):
    rejection_reason: str = Field(..., min_length=1)


# Theses proposals
class RetrieveThesesProposalResponse(BaseDTO):
    theses_proposal_id: str
    user_id: str
    stock_id: str
    proposed_change: dict[str, Any]
    llm_rationale: str | None
    llm_confidence: Decimal | None
    source_article_url: str | None
    source_evaluation_id: str
    theses_proposal_status: str
    rejection_reason: str | None
    resolved_at: datetime | None


class RetrieveAllThesesProposalResponse(BaseDTO):
    theses_proposals: list[RetrieveThesesProposalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Quant proposals
class RetrieveQuantProposalResponse(BaseDTO):
    quant_proposal_id: str
    theses_id: str
    quant_condition_id: str | None
    proposal_type: str
    proposed_change: dict[str, Any]
    llm_rationale: str | None
    llm_confidence: Decimal | None
    source_article_url: str | None
    source_evaluation_id: str
    quant_proposal_status: str
    rejection_reason: str | None
    resolved_at: datetime | None


class RetrieveAllQuantProposalResponse(BaseDTO):
    quant_proposals: list[RetrieveQuantProposalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Catalyst proposals
class RetrieveCatalystProposalResponse(BaseDTO):
    catalyst_proposal_id: str
    theses_id: str
    catalyst_id: str | None
    proposal_type: str
    proposed_change: dict[str, Any]
    llm_rationale: str | None
    llm_confidence: Decimal | None
    source_article_url: str | None
    source_evaluation_id: str
    catalyst_proposal_status: str
    rejection_reason: str | None
    resolved_at: datetime | None


class RetrieveAllCatalystProposalResponse(BaseDTO):
    catalyst_proposals: list[RetrieveCatalystProposalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Retrieve All Proposals
class RetrieveAllProposalsResponse(BaseDTO):
    theses_proposals: RetrieveAllThesesProposalResponse
    quant_proposals: RetrieveAllQuantProposalResponse
    catalyst_proposals: RetrieveAllCatalystProposalResponse
