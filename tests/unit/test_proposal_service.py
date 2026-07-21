"""
Unit tests for ProposalService.

Covers:
  - Not-found guards on every proposal type (theses / quant / catalyst)
  - Status guard: approving/rejecting a non-PENDING proposal raises 409
  - Approve quant: ADD creates a new condition, UPDATE patches existing,
    REMOVE deletes existing, invalid type raises 422
  - Approve catalyst: same three branches + invalid type
  - Approve theses: creates theses + bulk sub-resources
  - Reject: status always moves to REJECTED regardless of proposal type
  - _check_status is a static method — tested directly
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exception_handler import (
    QuantProposalNotFoundException,
    ThesesProposalNotFoundException,
    CatalystProposalNotFoundException,
    InvalidProposalStatusException,
    QuantConditionNotFoundException,
    CatalystNotFoundException,
    InvalidProposalTypeException,
)
from app.service.proposal_service import ProposalService
from common.enums.ProposalEnum import ProposalStatusEnum, ProposalTypeEnum


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _make_service(
        theses_repo=None,
        theses_proposal_repo=None,
        quant_condition_repo=None,
        quant_proposal_repo=None,
        catalyst_repo=None,
        catalyst_proposal_repo=None,
) -> ProposalService:
    return ProposalService(
        theses_repository=theses_repo or AsyncMock(),
        theses_proposal_repository=theses_proposal_repo or AsyncMock(),
        quant_condition_repository=quant_condition_repo or AsyncMock(),
        quant_proposal_repository=quant_proposal_repo or AsyncMock(),
        catalyst_repository=catalyst_repo or AsyncMock(),
        catalyst_proposal_repository=catalyst_proposal_repo or AsyncMock(),
    )

def common_proposal_fields(p: MagicMock):
    p.source_evaluation_id = _uid()
    p.created_at = datetime.now()
    p.updated_at = datetime.now()
    p.llm_rationale = None
    p.llm_confidence = None
    p.source_article_url = None
    p.rejection_reason = None
    p.resolved_at = None

def _pending_quant_proposal(
        proposal_type: ProposalTypeEnum = ProposalTypeEnum.UPDATE,
        proposed_change: dict | None = None,
        quant_condition_id: str | None = None,
        theses_id: str | None = None,
) -> MagicMock:
    p = MagicMock()
    p.quant_proposal_id = _uid()
    p.quant_proposal_status = ProposalStatusEnum.PENDING
    p.proposal_type = proposal_type
    p.theses_id = theses_id or _uid()
    p.quant_condition_id = quant_condition_id or _uid()
    p.proposed_change = proposed_change or {"metric": "forward_pe", "operator": "<", "value": "28"}
    common_proposal_fields(p)
    return p


def _pending_catalyst_proposal(
        proposal_type: ProposalTypeEnum = ProposalTypeEnum.UPDATE,
        proposed_change: dict | None = None,
        catalyst_id: str | None = None,
        theses_id: str | None = None,
) -> MagicMock:
    p = MagicMock()
    p.catalyst_proposal_id = _uid()
    p.catalyst_proposal_status = ProposalStatusEnum.PENDING
    p.proposal_type = proposal_type
    p.theses_id = theses_id or _uid()
    p.catalyst_id = catalyst_id or _uid()
    p.proposed_change = proposed_change or {"state": "confirmed", "description": "contract signed"}
    common_proposal_fields(p)
    return p


def _pending_theses_proposal(user_id: str, stock_id: str | None = None) -> MagicMock:
    p = MagicMock()
    p.theses_proposal_id = _uid()
    p.theses_proposal_status = ProposalStatusEnum.PENDING
    p.user_id = user_id
    p.stock_id = stock_id or _uid()
    p.proposed_change = {
        "quant_mode": "ANY",
        "catalyst_mode": "ANY",
        "notes": "proposed note",
        "quant_conditions": [],
        "catalysts": [],
    }
    common_proposal_fields(p)
    return p


def _approved_result(proposal: MagicMock) -> MagicMock:
    """Simulate what the repo returns after approve/reject."""
    r = MagicMock()
    r.__dict__ = {k: v for k, v in proposal.__dict__.items()}
    return r


# ---------------------------------------------------------------------------
# _check_status (static)
# ---------------------------------------------------------------------------

class TestCheckStatus:
    def test_passes_for_pending(self):
        # Should not raise
        ProposalService._check_status(ProposalStatusEnum.PENDING)

    @pytest.mark.parametrize("status", [
        ProposalStatusEnum.APPROVED,
        ProposalStatusEnum.REJECTED,
        ProposalStatusEnum.SUPERSEDED,
    ])
    def test_raises_for_non_pending(self, status):
        with pytest.raises(InvalidProposalStatusException):
            ProposalService._check_status(status)


# ---------------------------------------------------------------------------
# Quant proposal — not found
# ---------------------------------------------------------------------------

class TestQuantProposalNotFound:
    async def test_approve_raises_when_not_found(self):
        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = None

        svc = _make_service(quant_proposal_repo=quant_proposal_repo)

        with pytest.raises(QuantProposalNotFoundException):
            await svc.approve_quant_proposal(_uid(), _uid())

    async def test_reject_raises_when_not_found(self):
        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = None

        svc = _make_service(quant_proposal_repo=quant_proposal_repo)

        with pytest.raises(QuantProposalNotFoundException):
            await svc.reject_quant_proposal(_uid(), _uid(), "no thanks")

    async def test_approve_raises_when_already_approved(self):
        proposal = _pending_quant_proposal()
        proposal.quant_proposal_status = ProposalStatusEnum.APPROVED

        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = proposal

        svc = _make_service(quant_proposal_repo=quant_proposal_repo)

        with pytest.raises(InvalidProposalStatusException):
            await svc.approve_quant_proposal(_uid(), _uid())


# ---------------------------------------------------------------------------
# Quant proposal — ADD branch
# ---------------------------------------------------------------------------

class TestApproveQuantProposalAdd:
    async def test_creates_new_condition(self):
        user_id = _uid()
        change = {"metric": "pb_ratio", "operator": "<", "value": "2.5"}
        proposal = _pending_quant_proposal(proposal_type=ProposalTypeEnum.ADD, proposed_change=change)

        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = proposal
        quant_proposal_repo.approve_quant_proposal.return_value = proposal

        quant_condition_repo = AsyncMock()

        svc = _make_service(
            quant_proposal_repo=quant_proposal_repo,
            quant_condition_repo=quant_condition_repo,
        )

        await svc.approve_quant_proposal(proposal.quant_proposal_id, user_id)

        quant_condition_repo.create_quant_condition.assert_awaited_once_with(
            theses_id=proposal.theses_id,
            metric="pb_ratio",
            operator="<",
            value="2.5",
        )
        # An ADD never calls update or delete
        quant_condition_repo.update_quant_condition.assert_not_awaited()
        quant_condition_repo.delete_quant_condition.assert_not_awaited()


# ---------------------------------------------------------------------------
# Quant proposal — UPDATE branch
# ---------------------------------------------------------------------------

class TestApproveQuantProposalUpdate:
    async def test_updates_existing_condition(self):
        user_id = _uid()
        condition_id = _uid()
        theses_id = _uid()
        change = {"metric": "forward_pe", "operator": "<", "value": "30"}
        proposal = _pending_quant_proposal(
            proposal_type=ProposalTypeEnum.UPDATE,
            proposed_change=change,
            quant_condition_id=condition_id,
            theses_id=theses_id,
        )

        condition = MagicMock()
        quant_condition_repo = AsyncMock()
        quant_condition_repo.get_quant_condition_by_id_and_user.return_value = condition

        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = proposal
        quant_proposal_repo.approve_quant_proposal.return_value = proposal

        svc = _make_service(
            quant_proposal_repo=quant_proposal_repo,
            quant_condition_repo=quant_condition_repo,
        )

        await svc.approve_quant_proposal(proposal.quant_proposal_id, user_id)

        quant_condition_repo.update_quant_condition.assert_awaited_once()
        quant_proposal_repo.supersede_pending_updates.assert_awaited_once_with(
            quant_condition_id=condition_id,
            approved_proposal_id=proposal.quant_proposal_id,
        )

    async def test_raises_when_condition_missing(self):
        """The quant condition was deleted after the proposal was generated."""
        user_id = _uid()
        proposal = _pending_quant_proposal(proposal_type=ProposalTypeEnum.UPDATE)

        quant_condition_repo = AsyncMock()
        quant_condition_repo.get_quant_condition_by_id_and_user.return_value = None

        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = proposal

        svc = _make_service(
            quant_proposal_repo=quant_proposal_repo,
            quant_condition_repo=quant_condition_repo,
        )

        with pytest.raises(QuantConditionNotFoundException):
            await svc.approve_quant_proposal(proposal.quant_proposal_id, user_id)


# ---------------------------------------------------------------------------
# Quant proposal — REMOVE branch
# ---------------------------------------------------------------------------

class TestApproveQuantProposalRemove:
    async def test_deletes_existing_condition(self):
        user_id = _uid()
        condition = MagicMock()

        proposal = _pending_quant_proposal(proposal_type=ProposalTypeEnum.REMOVE)

        quant_condition_repo = AsyncMock()
        quant_condition_repo.get_quant_condition_by_id_and_user.return_value = condition

        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = proposal
        quant_proposal_repo.approve_quant_proposal.return_value = proposal

        svc = _make_service(
            quant_proposal_repo=quant_proposal_repo,
            quant_condition_repo=quant_condition_repo,
        )

        await svc.approve_quant_proposal(proposal.quant_proposal_id, user_id)

        quant_condition_repo.delete_quant_condition.assert_awaited_once_with(condition)
        quant_condition_repo.update_quant_condition.assert_not_awaited()


# ---------------------------------------------------------------------------
# Quant proposal — invalid type
# ---------------------------------------------------------------------------

class TestApproveQuantProposalInvalidType:
    async def test_raises_invalid_proposal_type(self):
        user_id = _uid()
        proposal = _pending_quant_proposal(proposal_type=ProposalTypeEnum.UPDATE)
        proposal.proposal_type = "BOGUS"  # bypass enum — simulate bad DB value

        condition = MagicMock()
        quant_condition_repo = AsyncMock()
        quant_condition_repo.get_quant_condition_by_id_and_user.return_value = condition

        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = proposal

        svc = _make_service(
            quant_proposal_repo=quant_proposal_repo,
            quant_condition_repo=quant_condition_repo,
        )

        with pytest.raises(InvalidProposalTypeException):
            await svc.approve_quant_proposal(proposal.quant_proposal_id, user_id)


# ---------------------------------------------------------------------------
# Quant proposal — reject
# ---------------------------------------------------------------------------

class TestRejectQuantProposal:
    async def test_reject_stores_reason(self):
        user_id = _uid()
        proposal = _pending_quant_proposal()
        rejected = MagicMock()
        rejected.__dict__ = {**proposal.__dict__, "quant_proposal_status": ProposalStatusEnum.REJECTED}

        quant_proposal_repo = AsyncMock()
        quant_proposal_repo.get_by_quant_proposal_id_and_user_id.return_value = proposal
        quant_proposal_repo.reject_quant_proposal.return_value = rejected

        svc = _make_service(quant_proposal_repo=quant_proposal_repo)
        result = await svc.reject_quant_proposal(proposal.quant_proposal_id, user_id, "stale data")

        quant_proposal_repo.reject_quant_proposal.assert_awaited_once_with(proposal, "stale data")


# ---------------------------------------------------------------------------
# Catalyst proposal — ADD / UPDATE / REMOVE
# ---------------------------------------------------------------------------

class TestApproveCatalystProposalAdd:
    async def test_creates_catalyst_from_proposal(self):
        user_id = _uid()
        change = {"state": "unconfirmed", "description": "FDA approval expected Q3"}
        proposal = _pending_catalyst_proposal(proposal_type=ProposalTypeEnum.ADD, proposed_change=change)

        catalyst_repo = AsyncMock()
        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = proposal
        catalyst_proposal_repo.approve_catalyst_proposal.return_value = proposal

        svc = _make_service(
            catalyst_repo=catalyst_repo,
            catalyst_proposal_repo=catalyst_proposal_repo,
        )

        await svc.approve_catalyst_proposal(proposal.catalyst_proposal_id, user_id)

        catalyst_repo.create_catalyst.assert_awaited_once_with(
            theses_id=proposal.theses_id,
            state="unconfirmed",
            description="FDA approval expected Q3",
            evidence=None,
        )


class TestApproveCatalystProposalUpdate:
    async def test_updates_catalyst_and_supersedes(self):
        user_id = _uid()
        catalyst_id = _uid()
        theses_id = _uid()
        change = {"state": "confirmed", "description": "contract signed"}
        proposal = _pending_catalyst_proposal(
            proposal_type=ProposalTypeEnum.UPDATE,
            proposed_change=change,
            catalyst_id=catalyst_id,
            theses_id=theses_id,
        )

        catalyst = MagicMock()
        catalyst_repo = AsyncMock()
        catalyst_repo.get_catalyst_by_id_and_user.return_value = catalyst

        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = proposal
        catalyst_proposal_repo.approve_catalyst_proposal.return_value = proposal

        svc = _make_service(
            catalyst_repo=catalyst_repo,
            catalyst_proposal_repo=catalyst_proposal_repo,
        )

        await svc.approve_catalyst_proposal(proposal.catalyst_proposal_id, user_id)

        catalyst_repo.update_catalyst.assert_awaited_once()
        catalyst_proposal_repo.supersede_pending_updates.assert_awaited_once_with(
            catalyst_id=catalyst_id,
            approved_proposal_id=proposal.catalyst_proposal_id,
        )

    async def test_raises_when_catalyst_missing(self):
        user_id = _uid()
        proposal = _pending_catalyst_proposal(proposal_type=ProposalTypeEnum.UPDATE)

        catalyst_repo = AsyncMock()
        catalyst_repo.get_catalyst_by_id_and_user.return_value = None

        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = proposal

        svc = _make_service(
            catalyst_repo=catalyst_repo,
            catalyst_proposal_repo=catalyst_proposal_repo,
        )

        with pytest.raises(CatalystNotFoundException):
            await svc.approve_catalyst_proposal(proposal.catalyst_proposal_id, user_id)


class TestApproveCatalystProposalRemove:
    async def test_deletes_catalyst(self):
        user_id = _uid()
        catalyst = MagicMock()
        proposal = _pending_catalyst_proposal(proposal_type=ProposalTypeEnum.REMOVE)

        catalyst_repo = AsyncMock()
        catalyst_repo.get_catalyst_by_id_and_user.return_value = catalyst

        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = proposal
        catalyst_proposal_repo.approve_catalyst_proposal.return_value = proposal

        svc = _make_service(
            catalyst_repo=catalyst_repo,
            catalyst_proposal_repo=catalyst_proposal_repo,
        )

        await svc.approve_catalyst_proposal(proposal.catalyst_proposal_id, user_id)

        catalyst_repo.delete_catalyst.assert_awaited_once_with(catalyst)
        catalyst_repo.update_catalyst.assert_not_awaited()


class TestApproveCatalystProposalInvalidType:
    async def test_raises_invalid_type(self):
        user_id = _uid()
        proposal = _pending_catalyst_proposal(proposal_type=ProposalTypeEnum.UPDATE)
        proposal.proposal_type = "UNKNOWN"

        catalyst = MagicMock()
        catalyst_repo = AsyncMock()
        catalyst_repo.get_catalyst_by_id_and_user.return_value = catalyst

        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = proposal

        svc = _make_service(
            catalyst_repo=catalyst_repo,
            catalyst_proposal_repo=catalyst_proposal_repo,
        )

        with pytest.raises(InvalidProposalTypeException):
            await svc.approve_catalyst_proposal(proposal.catalyst_proposal_id, user_id)


# ---------------------------------------------------------------------------
# Theses proposal — not found / status guard
# ---------------------------------------------------------------------------

class TestThesesProposalNotFound:
    async def test_approve_raises_when_not_found(self):
        theses_proposal_repo = AsyncMock()
        theses_proposal_repo.get_by_theses_proposal_id_and_user_id.return_value = None

        svc = _make_service(theses_proposal_repo=theses_proposal_repo)

        with pytest.raises(ThesesProposalNotFoundException):
            await svc.approve_theses_proposal(_uid(), _uid())

    async def test_reject_raises_when_not_found(self):
        theses_proposal_repo = AsyncMock()
        theses_proposal_repo.get_by_theses_proposal_id_and_user_id.return_value = None

        svc = _make_service(theses_proposal_repo=theses_proposal_repo)

        with pytest.raises(ThesesProposalNotFoundException):
            await svc.reject_theses_proposal(_uid(), _uid(), "rejected")


# ---------------------------------------------------------------------------
# Theses proposal — approve creates thesis + sub-resources
# ---------------------------------------------------------------------------

class TestApproveThesesProposal:
    async def test_creates_theses_and_sub_resources(self):
        user_id = _uid()
        proposal = _pending_theses_proposal(user_id)
        proposal.proposed_change = {
            "quant_mode": "ANY",
            "catalyst_mode": "ANY",
            "notes": "new thesis via proposal",
            "quant_conditions": [{"metric": "forward_pe", "operator": "<", "value": "25"}],
            "catalysts": [{"state": "unconfirmed", "description": "contract win"}],
        }

        theses = MagicMock()
        theses.theses_id = _uid()

        theses_repo = AsyncMock()
        theses_repo.create_theses.return_value = theses

        theses_proposal_repo = AsyncMock()
        theses_proposal_repo.get_by_theses_proposal_id_and_user_id.return_value = proposal
        theses_proposal_repo.approve_theses_proposal.return_value = proposal

        quant_condition_repo = AsyncMock()
        catalyst_repo = AsyncMock()

        svc = _make_service(
            theses_repo=theses_repo,
            theses_proposal_repo=theses_proposal_repo,
            quant_condition_repo=quant_condition_repo,
            catalyst_repo=catalyst_repo,
        )

        await svc.approve_theses_proposal(proposal.theses_proposal_id, user_id)

        theses_repo.create_theses.assert_awaited_once_with(
            user_id=user_id,
            stock_id=proposal.stock_id,
            quant_mode="ANY",
            catalyst_mode="ANY",
            notes="new thesis via proposal",
        )
        quant_condition_repo.bulk_create_quant_condition.assert_awaited_once()
        catalyst_repo.bulk_create_catalysts.assert_awaited_once()
        theses_proposal_repo.approve_theses_proposal.assert_awaited_once_with(proposal)

    async def test_reject_stores_reason(self):
        user_id = _uid()
        proposal = _pending_theses_proposal(user_id)
        rejected = MagicMock()
        rejected.__dict__ = {**proposal.__dict__, "theses_proposal_status": ProposalStatusEnum.REJECTED}

        theses_proposal_repo = AsyncMock()
        theses_proposal_repo.get_by_theses_proposal_id_and_user_id.return_value = proposal
        theses_proposal_repo.reject_theses_proposal.return_value = rejected

        svc = _make_service(theses_proposal_repo=theses_proposal_repo)
        await svc.reject_theses_proposal(proposal.theses_proposal_id, user_id, "bad reasoning")

        theses_proposal_repo.reject_theses_proposal.assert_awaited_once_with(proposal, "bad reasoning")


# ---------------------------------------------------------------------------
# Catalyst proposal — not found / status guard
# ---------------------------------------------------------------------------

class TestCatalystProposalNotFound:
    async def test_approve_raises_when_not_found(self):
        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = None

        svc = _make_service(catalyst_proposal_repo=catalyst_proposal_repo)

        with pytest.raises(CatalystProposalNotFoundException):
            await svc.approve_catalyst_proposal(_uid(), _uid())

    async def test_reject_raises_when_not_found(self):
        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = None

        svc = _make_service(catalyst_proposal_repo=catalyst_proposal_repo)

        with pytest.raises(CatalystProposalNotFoundException):
            await svc.reject_catalyst_proposal(_uid(), _uid(), "rejected")

    async def test_approve_raises_for_non_pending_status(self):
        user_id = _uid()
        proposal = _pending_catalyst_proposal()
        proposal.catalyst_proposal_status = ProposalStatusEnum.APPROVED

        catalyst_proposal_repo = AsyncMock()
        catalyst_proposal_repo.get_by_catalyst_proposal_id_and_user_id.return_value = proposal

        svc = _make_service(catalyst_proposal_repo=catalyst_proposal_repo)

        with pytest.raises(InvalidProposalStatusException):
            await svc.approve_catalyst_proposal(proposal.catalyst_proposal_id, user_id)
